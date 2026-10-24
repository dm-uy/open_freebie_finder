"""Bounded, non-mutating validation of OpenAI-compatible provider endpoints."""
import asyncio
import json
import logging
import os
import re
import time
from contextvars import ContextVar
from urllib.parse import urlsplit

import httpx

from backend.app.config import Settings, get_settings
from backend.app.core.providers.models import ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry, get_registry
from backend.app.core.providers.validation_models import (
    ProviderValidationReport,
    ProviderValidationRequest,
    ValidationCheck,
)

TOTAL_TIMEOUT = 20.0
STAGE_TIMEOUT = 10.0
MAX_BODY_BYTES = 1024 * 1024
_TOKEN = re.compile(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+\Z")
_RESERVED = {"host", "content-length", "content-type", "accept", "connection", "transfer-encoding"}
_MESSAGES = {
    "missing_credentials": "Provider credentials are required.",
    "invalid_configuration": "Provider configuration is invalid.",
    "invalid_catalog": "Model catalog protocol is invalid.",
    "no_eligible_models": "No eligible models found.",
    "model_not_eligible": "Requested model is not eligible.",
    "invalid_completion": "Completion protocol is invalid.",
    "timeout": "Provider validation timed out.",
    "response_too_large": "Provider response exceeded the size limit.",
    "connection_error": "Provider connection failed.",
    "upstream_auth_error": "Provider rejected authentication.",
    "rate_limited": "Provider rate limit reached.",
    "upstream_unavailable": "Provider is unavailable.",
    "upstream_http_error": "Provider returned an unsuccessful HTTP status.",
}

# HTTP libraries otherwise log URLs and, at DEBUG, response headers. Suppress only
# records originating in a validation context; other proxy requests keep their logs.
_private_http = ContextVar("provider_validation_private_http", default=False)


class _PrivateHTTPFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _private_http.get()


for _logger_name in ("httpx", "httpcore.connection", "httpcore.http11", "httpcore.http2", "httpcore.proxy"):
    logging.getLogger(_logger_name).addFilter(_PrivateHTTPFilter())


class ProviderNotFound(Exception):
    """A provider ID is not present in the registry."""


class _Failure(Exception):
    def __init__(self, code: str, http_status: int | None = None):
        self.code = code
        self.http_status = http_status


def _origin(value: str) -> tuple[str, str, int]:
    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"} or not parsed.hostname
            or "@" in parsed.netloc or "?" in value or "#" in value
            or any(c in value for c in "{}\r\n\t")
            or any(c.isspace() for c in value)
        ):
            raise ValueError
        port = parsed.port
        if port is not None and not 1 <= port <= 65535:
            raise ValueError
        # Ensure the actual HTTP client can parse the same URL before any I/O.
        httpx.URL(value)
        return parsed.scheme, parsed.hostname.lower(), port or (443 if parsed.scheme == "https" else 80)
    except (ValueError, httpx.InvalidURL):
        raise _Failure("invalid_configuration") from None


def _valid_id(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip()) and len(value) <= 512


class ProviderValidationService:
    """Perform at most one catalog GET and one completion POST per validation."""

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        settings: Settings | None = None,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.registry = registry if registry is not None else get_registry()
        self.settings = settings if settings is not None else get_settings()
        self.transport = transport

    def _configuration(self, manifest: ProviderManifest, key: str | None) -> dict[str, str]:
        base_origin = _origin(manifest.base_url)
        catalog_origin = _origin(manifest.models_endpoint)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if manifest.auth.type == "none":
            if key is not None:
                raise _Failure("invalid_configuration")
        else:
            if not key:
                raise _Failure("missing_credentials")
            if any(c in key for c in "\r\n") or not key.isascii():
                raise _Failure("invalid_configuration")
            if base_origin != catalog_origin:
                raise _Failure("invalid_configuration")
            if manifest.auth.type == "bearer":
                headers["Authorization"] = f"Bearer {key}"
            else:
                name = manifest.auth.custom_header_name or ""
                if not _TOKEN.fullmatch(name) or name.lower() in _RESERVED:
                    raise _Failure("invalid_configuration")
                headers[name] = key
        rule = manifest.discovery
        if rule.type == "regex":
            pattern = rule.filter_expression
            if not pattern or len(pattern) > 256:
                raise _Failure("invalid_configuration")
            try:
                re.compile(pattern)
            except (re.error, OverflowError, RecursionError):
                raise _Failure("invalid_configuration") from None
        if rule.type == "manual" and (not rule.static_models or not all(map(_valid_id, rule.static_models))):
            raise _Failure("invalid_configuration")
        return headers

    async def _fetch(
        self, client: httpx.AsyncClient, method: str, url: str,
        deadline: float, invalid_code: str, headers: dict[str, str], payload: dict | None = None,
    ) -> tuple[object, int]:
        status = None
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise _Failure("timeout")
        timeout = min(STAGE_TIMEOUT, remaining)
        try:
            async with asyncio.timeout(timeout):
                async with client.stream(method, url, headers=headers, json=payload, timeout=timeout) as response:
                    status = response.status_code
                    if status != 200:
                        if status in (401, 403):
                            code = "upstream_auth_error"
                        elif status == 429:
                            code = "rate_limited"
                        elif 500 <= status <= 599:
                            code = "upstream_unavailable"
                        else:
                            code = "upstream_http_error"
                        raise _Failure(code, status)
                    body = bytearray()
                    async for chunk in response.aiter_bytes():
                        if len(body) + len(chunk) > MAX_BODY_BYTES:
                            raise _Failure("response_too_large", status)
                        body.extend(chunk)
                    try:
                        return json.loads(body), status
                    except (ValueError, UnicodeError, RecursionError):
                        raise _Failure(invalid_code, status) from None
        except (TimeoutError, httpx.TimeoutException):
            raise _Failure("timeout", status) from None
        except (httpx.RequestError, httpx.InvalidURL):
            raise _Failure("connection_error", status) from None

    def _catalog(self, manifest: ProviderManifest, data: object, secrets: list[str]) -> list[str]:
        rule = manifest.discovery
        if rule.type == "manual":
            entries = [{rule.model_id_field: value} for value in rule.static_models]
        else:
            if not isinstance(data, dict) or not isinstance(data.get("data"), list):
                raise _Failure("invalid_catalog", 200)
            entries = data["data"]
        ids = set()
        for item in entries:
            if not isinstance(item, dict):
                continue
            model_id = item.get(rule.model_id_field)
            if not _valid_id(model_id) or any(secret in model_id for secret in secrets):
                continue
            if rule.type == "openrouter_free":
                pricing = item.get("pricing")
                if not isinstance(pricing, dict) or not all(
                    str(pricing.get(field, "")).strip() in {"0", "0.0", "0.00"}
                    for field in ("prompt", "completion")
                ):
                    continue
            if rule.type == "regex" and not re.search(rule.filter_expression, model_id):
                continue
            ids.add(model_id)
        if not ids:
            raise _Failure("no_eligible_models", None if rule.type == "manual" else 200)
        return sorted(ids)

    @staticmethod
    def _check_completion(data: object) -> None:
        if isinstance(data, dict) and "error" not in data:
            choices = data.get("choices")
            if isinstance(choices, list) and choices and isinstance(choices[0], dict):
                message = choices[0].get("message")
                if (
                    isinstance(message, dict) and message.get("role") == "assistant"
                    and "content" in message and (message["content"] is None or isinstance(message["content"], str))
                ):
                    return
        raise _Failure("invalid_completion", 200)

    async def validate(self, request: ProviderValidationRequest) -> ProviderValidationReport:
        start = time.monotonic()
        manifest = request.manifest
        if manifest is None:
            manifest = self.registry.get_manifest(request.provider_id)
            if manifest is None:
                raise ProviderNotFound
        key = request.api_key.get_secret_value() if request.api_key is not None else None
        if request.manifest is None and key is None and manifest.auth.type != "none" and manifest.auth.api_key_env:
            env_name = manifest.auth.api_key_env
            key = os.getenv(env_name) or getattr(self.settings, env_name.lower(), None)
        secrets = sorted({s for s in (key, self.settings.proxy_master_key) if s}, key=len, reverse=True)
        provider_id = manifest.id
        for secret in secrets:
            provider_id = provider_id.replace(secret, "[REDACTED]")
        report = ProviderValidationReport(provider_id=provider_id)
        stage = "configuration"
        stage_start = start
        token = _private_http.set(True)
        try:
            headers = self._configuration(manifest, key)
            report.checks.append(ValidationCheck(
                name=stage, status="passed", duration_ms=(time.monotonic()-stage_start)*1000,
                message="Configuration accepted.",
            ))
            deadline = time.monotonic() + TOTAL_TIMEOUT
            async with httpx.AsyncClient(transport=self.transport, trust_env=False, follow_redirects=False) as client:
                stage = "catalog"
                stage_start = time.monotonic()
                manual = manifest.discovery.type == "manual"
                data = None
                if not manual:
                    data, _ = await self._fetch(client, "GET", manifest.models_endpoint, deadline, "invalid_catalog", headers)
                ids = self._catalog(manifest, data, secrets)
                if request.model_id is not None and request.model_id not in ids:
                    raise _Failure("model_not_eligible", None if manual else 200)
                report.model_id = request.model_id or ids[0]
                report.model_ids = ids[:100]
                report.eligible_model_count = len(ids)
                report.checks.append(ValidationCheck(
                    name=stage, status="passed", code="manual_catalog" if manual else None,
                    http_status=None if manual else 200, duration_ms=(time.monotonic()-stage_start)*1000,
                    message="Manual model catalog accepted." if manual else "Eligible models found.",
                ))
                stage = "completion"
                stage_start = time.monotonic()
                url = manifest.base_url.rstrip("/")
                if not url.endswith("/chat/completions"):
                    url += "/chat/completions"
                data, _ = await self._fetch(client, "POST", url, deadline, "invalid_completion", headers, {
                    "model": report.model_id,
                    "messages": [{"role": "user", "content": "Reply OK."}],
                    "stream": False, "max_tokens": 16,
                })
                self._check_completion(data)
                report.checks.append(ValidationCheck(
                    name=stage, status="passed", http_status=200,
                    duration_ms=(time.monotonic()-stage_start)*1000, message="Completion protocol verified.",
                ))
            report.valid = True
        except _Failure as exc:
            report.checks.append(ValidationCheck(
                name=stage, status="failed", code=exc.code, http_status=exc.http_status,
                duration_ms=(time.monotonic()-stage_start)*1000, message=_MESSAGES[exc.code],
            ))
        finally:
            _private_http.reset(token)
        for name in ("configuration", "catalog", "completion")[len(report.checks):]:
            report.checks.append(ValidationCheck(
                name=name, status="skipped", code="previous_check_failed", message="Previous check failed.",
            ))
        report.total_duration_ms = (time.monotonic()-start)*1000
        return report
