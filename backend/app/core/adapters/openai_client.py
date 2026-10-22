"""Universal Async OpenAI-compatible Provider Client."""
import json
import logging
import os
from typing import Any, AsyncGenerator, Optional
import httpx
from backend.app.config import get_settings
from backend.app.core.providers.models import ProviderManifest

logger = logging.getLogger(__name__)


class UpstreamRateLimitError(Exception):
    """Raised when an upstream provider returns 429 Too Many Requests or rate limit in stream."""

    def __init__(self, message: str, provider_id: str, raw_model_id: str) -> None:
        super().__init__(message)
        self.provider_id = provider_id
        self.raw_model_id = raw_model_id


class UpstreamProviderError(Exception):
    """Raised when an upstream provider returns 5xx or connection error."""

    def __init__(self, message: str, status_code: int, provider_id: str, raw_model_id: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.provider_id = provider_id
        self.raw_model_id = raw_model_id


class OpenAIProviderClient:
    """Dispatches chat completions to OpenAI-compatible upstream providers."""

    def __init__(self, http_client: Optional[httpx.AsyncClient] = None) -> None:
        self._external_client = http_client

    def _build_headers(self, manifest: ProviderManifest) -> dict[str, str]:
        """Build HTTP headers including authentication for the upstream provider."""
        settings = get_settings()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "open-freebie-finder/0.1.0",
        }

        if manifest.auth.type == "bearer" and manifest.auth.api_key_env:
            key = os.getenv(manifest.auth.api_key_env) or getattr(settings, manifest.auth.api_key_env.lower(), None)
            if key:
                headers["Authorization"] = f"Bearer {key}"
        elif manifest.auth.type == "header" and manifest.auth.custom_header_name and manifest.auth.api_key_env:
            key = os.getenv(manifest.auth.api_key_env) or getattr(settings, manifest.auth.api_key_env.lower(), None)
            if key:
                headers[manifest.auth.custom_header_name] = key

        return headers

    def _get_completions_url(self, manifest: ProviderManifest) -> str:
        """Resolve completions URL from base_url."""
        base = manifest.base_url.rstrip("/")
        if base.endswith("/chat/completions"):
            return base
        return f"{base}/chat/completions"

    async def complete(
        self,
        manifest: ProviderManifest,
        raw_model_id: str,
        canonical_model: str,
        payload: dict[str, Any],
        timeout: float = 15.0,
    ) -> dict[str, Any]:
        """Execute non-streaming chat completion with canonical model name masking."""
        url = self._get_completions_url(manifest)
        headers = self._build_headers(manifest)

        # Clone and rewrite payload for upstream
        outbound = dict(payload)
        outbound["model"] = raw_model_id
        outbound["stream"] = False

        try:
            if self._external_client:
                response = await self._external_client.post(url, json=outbound, headers=headers, timeout=timeout)
            else:
                async with httpx.AsyncClient() as client:
                    response = await client.post(url, json=outbound, headers=headers, timeout=timeout)
        except (httpx.TimeoutException, httpx.ConnectError, httpx.RequestError) as exc:
            raise UpstreamProviderError(str(exc), 503, manifest.id, raw_model_id) from exc

        # Handle rate limits and server errors
        if response.status_code == 429:
            raise UpstreamRateLimitError(
                f"Rate limit exceeded on {manifest.id} ({raw_model_id})",
                manifest.id,
                raw_model_id,
            )
        if response.status_code != 200:
            # Check if error response body mentions rate limit
            try:
                err_body = response.json()
                msg = str(err_body.get("error", "")).lower()
                if "rate limit" in msg or "quota" in msg or "429" in msg:
                    raise UpstreamRateLimitError(msg, manifest.id, raw_model_id)
            except Exception:
                pass
            raise UpstreamProviderError(
                f"Upstream HTTP error ({response.status_code}) on {manifest.id}: {response.text[:200]}",
                response.status_code,
                manifest.id,
                raw_model_id,
            )

        data = response.json()

        # Canonical Model Masking: guarantee response reflects requested model name
        data["model"] = canonical_model

        # Guarantee usage block is present (AC-4 synthesis)
        if "usage" not in data or not data["usage"]:
            data["usage"] = {
                "prompt_tokens": 0,
                "completion_tokens": 0,
                "total_tokens": 0,
            }

        return data

    async def stream_complete(
        self,
        manifest: ProviderManifest,
        raw_model_id: str,
        canonical_model: str,
        payload: dict[str, Any],
        timeout: float = 15.0,
    ) -> AsyncGenerator[str, None]:
        """Execute streaming chat completion with first-token pre-buffering and model masking."""
        url = self._get_completions_url(manifest)
        headers = self._build_headers(manifest)
        headers["Accept"] = "text/event-stream"

        outbound = dict(payload)
        outbound["model"] = raw_model_id
        outbound["stream"] = True

        client = self._external_client or httpx.AsyncClient()
        should_close_client = self._external_client is None

        try:
            req = client.build_request("POST", url, json=outbound, headers=headers, timeout=timeout)
            resp = await client.send(req, stream=True)

            # Check status code immediately before reading stream
            if resp.status_code == 429:
                await resp.aclose()
                raise UpstreamRateLimitError(
                    f"Rate limit exceeded on {manifest.id} ({raw_model_id})",
                    manifest.id,
                    raw_model_id,
                )
            if resp.status_code >= 500:
                await resp.aclose()
                raise UpstreamProviderError(
                    f"Upstream server error ({resp.status_code}) on {manifest.id}",
                    resp.status_code,
                    manifest.id,
                    raw_model_id,
                )
            if resp.status_code != 200:
                await resp.aclose()
                raise UpstreamProviderError(
                    f"Upstream status error {resp.status_code} on {manifest.id}",
                    resp.status_code,
                    manifest.id,
                    raw_model_id,
                )

            # First-token pre-buffering: read chunks until first valid token or error
            lines_iterator = resp.aiter_lines()
            pre_buffered_lines: list[str] = []
            first_token_received = False

            async for line in lines_iterator:
                line_str = line.strip()
                if not line_str:
                    continue

                if line_str.startswith("data: "):
                    content = line_str[6:].strip()
                    if content == "[DONE]":
                        pre_buffered_lines.append(line_str)
                        break

                    try:
                        chunk_json = json.loads(content)
                        # Check for in-stream error object
                        if "error" in chunk_json:
                            err_msg = str(chunk_json.get("error", "")).lower()
                            await resp.aclose()
                            if "rate limit" in err_msg or "quota" in err_msg or "429" in err_msg:
                                raise UpstreamRateLimitError(err_msg, manifest.id, raw_model_id)
                            raise UpstreamProviderError(err_msg, 502, manifest.id, raw_model_id)

                        # Mask model in chunk JSON
                        chunk_json["model"] = canonical_model
                        pre_buffered_lines.append(f"data: {json.dumps(chunk_json)}")

                        # Check if this chunk delivered delta content
                        choices = chunk_json.get("choices", [])
                        if choices and isinstance(choices, list):
                            delta = choices[0].get("delta", {})
                            if delta.get("content") is not None or delta.get("role"):
                                first_token_received = True
                                break
                    except json.JSONDecodeError:
                        pre_buffered_lines.append(line_str)
                else:
                    pre_buffered_lines.append(line_str)

            # Yield pre-buffered chunks
            for buffered in pre_buffered_lines:
                yield f"{buffered}\n\n"

            # Continue streaming remaining chunks from upstream
            async for line in lines_iterator:
                line_str = line.strip()
                if not line_str:
                    continue

                if line_str.startswith("data: "):
                    content = line_str[6:].strip()
                    if content == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break

                    try:
                        chunk_json = json.loads(content)
                        chunk_json["model"] = canonical_model
                        yield f"data: {json.dumps(chunk_json)}\n\n"
                    except json.JSONDecodeError:
                        yield f"{line_str}\n\n"
                else:
                    yield f"{line_str}\n\n"

            await resp.aclose()
        finally:
            if should_close_client:
                await client.aclose()
