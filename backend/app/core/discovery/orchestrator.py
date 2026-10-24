"""Shared manifest-driven background discovery with isolated provider snapshots."""
import asyncio
import json
import re
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from contextlib import aclosing

import httpx

from backend.app.core.discovery.privacy import private_http
from backend.app.core.providers.models import DiscoveredModel, ProviderManifest
from backend.app.core.providers.registry import ProviderRegistry

PROVIDER_TIMEOUT = 15.0
MAX_CATALOG_BYTES = 4 * 1024 * 1024


class CatalogFailure(Exception):
    def __init__(self, code: str):
        self.code = code


@dataclass
class DiscoveryStatus:
    outcome: str
    code: str | None = None
    last_attempt_time: str | None = None
    last_success_time: str | None = None
    catalog_count: int = 0
    admitted_count: int = 0


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DiscoveryOrchestrator:
    def __init__(self, registry: ProviderRegistry, http_client: httpx.AsyncClient | None = None):
        self.registry = registry
        self._external_client = http_client
        self.statuses: dict[str, DiscoveryStatus] = {}
        self._cycle_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(4)
        from backend.app.core.eligibility.probes import ProbeWorker
        self.probes = ProbeWorker(registry)
        from backend.app.core.tasks.discovery import TaskDiscovery
        self.tasks = TaskDiscovery(self)

    def _headers(self, manifest: ProviderManifest) -> dict[str, str]:
        # Validation supplies the same protocol constraints without reusing its
        # credential resolution or mutating API. No completion is performed here.
        from urllib.parse import urlsplit
        from backend.app.core.eligibility.account import account_profile, account_bound
        from backend.app.core.eligibility.evidence import source_verdict
        if account_profile(manifest) and self.registry.eligibility.source is source_verdict and not account_bound(manifest):
            raise CatalogFailure("invalid_configuration")
        key = self.registry.credential(manifest)
        try:
            for value in (manifest.base_url, manifest.models_endpoint):
                url = urlsplit(value)
                if url.scheme not in {"http", "https"} or not url.hostname or "@" in url.netloc or url.query or url.fragment or any(c.isspace() for c in value):
                    raise ValueError
                if url.port is not None and not 1 <= url.port <= 65535:
                    raise ValueError
                httpx.URL(value)
            headers = {"Accept": "application/json"}
            if manifest.auth.type != "none":
                if not key or not key.isascii() or any(c in key for c in "\r\n"):
                    raise ValueError
                if manifest.auth.type == "bearer":
                    headers["Authorization"] = f"Bearer {key}"
                else:
                    name = manifest.auth.custom_header_name or ""
                    if not re.fullmatch(r"[!#$%&'*+.^_`|~0-9A-Za-z-]+", name) or name.lower() in {
                        "host", "content-length", "content-type", "accept", "connection", "transfer-encoding",
                    }:
                        raise ValueError
                    headers[name] = key
            rule = manifest.discovery
            if rule.type == "regex":
                if not rule.filter_expression or len(rule.filter_expression) > 256:
                    raise ValueError
                re.compile(rule.filter_expression)
            if rule.type == "manual" and (not rule.static_models or any(not v.strip() or len(v) > 512 for v in rule.static_models)):
                raise ValueError
            return headers
        except (ValueError, OverflowError, RecursionError, re.error, httpx.InvalidURL):
            raise CatalogFailure("invalid_configuration") from None

    async def _fetch(self, manifest: ProviderManifest, headers: dict[str, str]) -> object:
        async def read(client, url, request_headers, params=None):
            # Explicit requests prevent injected client auth/cookies/default
            # headers from crossing either of the owned source boundaries.
            request = httpx.Request("GET", url, headers=request_headers, params=params,
                                    extensions={"timeout": httpx.Timeout(PROVIDER_TIMEOUT).as_dict()})
            async with aclosing(await client.send(request, stream=True, auth=None,
                                                 follow_redirects=False)) as response:
                status = response.status_code
                if status != 200:
                    code = ("upstream_auth_error" if status in (401, 403) else "rate_limited" if status == 429
                            else "upstream_unavailable" if 500 <= status < 600 else "upstream_http_error")
                    raise CatalogFailure(code)
                body = bytearray()
                async for chunk in response.aiter_bytes():
                    if len(body) + len(chunk) > MAX_CATALOG_BYTES:
                        raise CatalogFailure("response_too_large")
                    body.extend(chunk)
                try:
                    return json.loads(body)
                except (ValueError, RecursionError):
                    raise CatalogFailure("invalid_catalog") from None
        async def snapshot(client):
            data = await read(client, manifest.models_endpoint, headers)
            from backend.app.core.eligibility.account import account_bound
            from backend.app.core.eligibility.evidence import source_verdict
            if (manifest.id == "nvidia_nim" and account_bound(manifest)
                    and self.registry.eligibility.source is source_verdict):
                from backend.app.core.discovery.nvidia import FREE_CATALOG_URL, FREE_CATALOG_QUERY, intersect_free_chat
                # Public source: never forward the inference key to NGC.
                source = await read(client, FREE_CATALOG_URL, {"Accept": "application/json"},
                                    {"q": FREE_CATALOG_QUERY})
                data = intersect_free_chat(data, source)
            return data
        try:
            with private_http():
                async with asyncio.timeout(PROVIDER_TIMEOUT):
                    if self._external_client is not None:
                        return await snapshot(self._external_client)
                    async with httpx.AsyncClient(trust_env=False, follow_redirects=False) as client:
                        return await snapshot(client)
        except (TimeoutError, httpx.TimeoutException):
            raise CatalogFailure("timeout") from None
        except httpx.RequestError:
            raise CatalogFailure("connection_error") from None

    def _parse(self, manifest: ProviderManifest, data: object) -> tuple[int, list[DiscoveredModel]]:
        from backend.app.core.eligibility.account import account_profile, parse_account_catalog
        from backend.app.core.eligibility.evidence import source_verdict
        if account_profile(manifest) and self.registry.eligibility.source is source_verdict:
            return parse_account_catalog(self.registry, manifest, data)
        rule = manifest.discovery
        if not isinstance(data, dict) or not isinstance(data.get("data"), list):
            raise CatalogFailure("invalid_catalog")
        info = data.get("result_info")
        if data.get("has_more") or data.get("next_cursor") or data.get("next"):
            raise CatalogFailure("incomplete_catalog")
        if isinstance(info, dict):
            try:
                if int(info.get("total_pages", 1)) > int(info.get("page", 1)):
                    raise CatalogFailure("incomplete_catalog")
            except (ValueError, TypeError, OverflowError):
                raise CatalogFailure("invalid_catalog") from None
        observed = {}
        conflicts = set()
        admitted = []
        for item in data["data"]:
            if not isinstance(item, dict):
                continue
            raw_id = item.get(rule.model_id_field)
            if not isinstance(raw_id, str) or not raw_id.strip() or len(raw_id) > 512:
                continue
            if raw_id in observed:
                if observed[raw_id] != item:
                    conflicts.add(raw_id)
                    admitted = [m for m in admitted if m.id != raw_id]
                continue
            if len(observed) >= 1000 or raw_id in conflicts:
                continue
            observed[raw_id] = item
            if self.registry.is_private_identifier(raw_id):
                continue
            if rule.type == "regex" and not re.search(rule.filter_expression, raw_id):
                continue
            # A declared negative capability always wins over an allowlist.
            capabilities = item.get("capabilities")
            if isinstance(capabilities, dict) and capabilities.get("completion_chat") is False:
                continue
            architecture = item.get("architecture")
            if isinstance(architecture, dict) and isinstance(architecture.get("output_modalities"), list) and "text" not in architecture["output_modalities"]:
                continue
            try:
                context = int(float(item.get(rule.context_length_field, 4096)))
                if context <= 0:
                    context = 4096
            except (ValueError, TypeError, OverflowError):
                context = 4096
            model = DiscoveredModel(id=raw_id, provider_id=manifest.id,
                canonical_name=self.registry.canonical_name(manifest, raw_id), context_window=context,
                metadata={k:item[k] for k in ("pricing", "architecture", "capabilities", "disabled", "supported_parameters") if k in item})
            admitted.append(model)
        return len(observed), admitted

    async def discover_provider(self, manifest: ProviderManifest) -> list[DiscoveredModel]:
        previous = self.statuses.get(manifest.id)
        status = DiscoveryStatus(outcome="failed", last_attempt_time=_now(),
            last_success_time=previous.last_success_time if previous else None,
            catalog_count=previous.catalog_count if previous else 0,
            admitted_count=previous.admitted_count if previous else 0)
        skip = self.registry.profile_skip(manifest)
        if skip:
            status.outcome = skip if skip in {"disabled", "missing_credentials", "retired", "excluded", "unsupported_profile"} else "failed"
            status.code = skip
            status.admitted_count = 0
            self.registry.eligibility.clear(manifest.id)
            self.statuses[manifest.id] = status
            return []
        try:
            scope = self.registry.eligibility.scope(manifest)
            headers = self._headers(manifest)
            if manifest.discovery.type == "manual":
                data = {"data": [{manifest.discovery.model_id_field: value} for value in manifest.discovery.static_models]}
            else:
                data = await self._fetch(manifest, headers)
            count, models = self._parse(manifest, data)
            if self.registry.eligibility.scope(manifest) != scope:
                raise CatalogFailure("credential_changed")
            await self.registry.register_models(models, provider_id=manifest.id)
            self.registry.eligibility.publish(manifest, {m.id:m.metadata for m in models}, scope)
            for model in models:
                evidence = self.registry.eligibility.get(manifest, model.id)
                model.is_free = evidence is not None and evidence.verdict.state == "free"
            eligible = [m for m in models if self.registry.admits(manifest, m)]
            status.outcome = "succeeded"
            status.code = "manual_catalog" if manifest.discovery.type == "manual" else None
            status.catalog_count = count
            status.admitted_count = len(eligible)
            status.last_success_time = _now()
            self.statuses[manifest.id] = status
            return eligible
        except asyncio.CancelledError:
            self.registry.eligibility.clear(manifest.id)
            status.code = "cancelled"
            status.admitted_count = 0
            self.statuses[manifest.id] = status
            raise
        except CatalogFailure as exc:
            self.registry.eligibility.clear(manifest.id)
            status.admitted_count = 0
            status.code = exc.code
            self.statuses[manifest.id] = status
            return []
        except Exception:
            self.registry.eligibility.clear(manifest.id)
            status.admitted_count = 0
            # Isolate unexpected/malformed provider state without logging its data.
            status.code = "invalid_configuration"
            self.statuses[manifest.id] = status
            return []

    async def run_cycle(self) -> dict[str, dict]:
        async with self._cycle_lock:
            manifests = self.registry.get_manifests()
            self.registry.eligibility.prune()
            self.registry.billing.prune(self.registry.eligibility.scope(p) for p in manifests)
            self.statuses = {key: value for key, value in self.statuses.items() if any(p.id == key for p in manifests)}
            for key in self.registry.invalid_profiles:
                self.statuses[key] = DiscoveryStatus(outcome="failed", code="invalid_configuration", last_attempt_time=_now())
            async def run(manifest):
                async with self._semaphore:
                    await self.discover_provider(manifest)
            try:
                async with asyncio.timeout(30):
                    await asyncio.gather(*(run(manifest) for manifest in manifests), *self.tasks.jobs())
            except TimeoutError:
                pass
            return {key: asdict(value) for key, value in self.statuses.items()}

    async def refresh_evidence(self):
        """Observe the source again without renewing the distinct catalog snapshot."""
        from backend.app.core.eligibility.evidence import openrouter_bound
        from backend.app.core.eligibility.account import account_bound
        async with self._cycle_lock:
            async def refresh(manifest):
                if self.registry.profile_skip(manifest):
                    self.registry.eligibility.clear(manifest.id)
                    return
                # Unsupported sources have no external proof to refresh.
                if not openrouter_bound(manifest) and not account_bound(manifest) and self.registry.eligibility.source.__module__ == "backend.app.core.eligibility.evidence":
                    return
                async with self._semaphore:
                    scope = self.registry.eligibility.scope(manifest)
                    try:
                        data = await self._fetch(manifest, self._headers(manifest))
                        _, models = self._parse(manifest, data)
                        if account_bound(manifest):
                            await self.registry.register_models(models, provider_id=manifest.id)
                        self.registry.eligibility.publish(manifest, {m.id:m.metadata for m in models}, scope)
                        for model in self.registry.get_models():
                            if model.provider_id == manifest.id:
                                record = self.registry.eligibility.get(manifest, model.id)
                                model.is_free = bool(record and record.verdict.state == "free")
                    except asyncio.CancelledError:
                        self.registry.eligibility.clear(manifest.id)
                        raise
                    except Exception:
                        self.registry.eligibility.clear(manifest.id)
            try:
                async with asyncio.timeout(30):
                    await asyncio.gather(*(refresh(p) for p in self.registry.get_manifests()), *self.tasks.jobs())
            except TimeoutError:
                # Targets whose work did not finish are no longer certified.
                for manifest in self.registry.get_manifests():
                    record_times = [r.observed_at for (p, _), r in self.registry.eligibility.records.items() if p == manifest.id]
                    if record_times and min(record_times) < time.monotonic() - 30:
                        self.registry.eligibility.clear(manifest.id)

    async def run(self, stop: asyncio.Event) -> None:
        probe_task = asyncio.create_task(self.probes.run(stop))
        try:
            await self._run_sources(stop)
        finally:
            probe_task.cancel()
            await asyncio.gather(probe_task, return_exceptions=True)

    async def _run_sources(self, stop: asyncio.Event) -> None:
        catalog_due = evidence_due = 0.0
        while not stop.is_set():
            now = time.monotonic()
            if now >= catalog_due:
                await self.run_cycle()
                catalog_due = time.monotonic() + max(1, self.registry.settings.discovery_interval_seconds)
                evidence_due = time.monotonic() + self.registry.settings.eligibility_refresh_seconds
            elif now >= evidence_due:
                await self.refresh_evidence()
                evidence_due = time.monotonic() + self.registry.settings.eligibility_refresh_seconds
            try:
                await asyncio.wait_for(stop.wait(), timeout=max(.01, min(catalog_due, evidence_due) - time.monotonic()))
            except TimeoutError:
                pass
