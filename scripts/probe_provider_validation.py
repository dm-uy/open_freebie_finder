"""Probe a running local provider-validation endpoint without printing secrets."""
import argparse
import asyncio
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit

# Support the documented direct-file command from the repository root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import httpx

from backend.app.config import get_settings
from backend.app.core.providers.validation_models import ProviderValidationReport


async def probe(base_url: str, provider_id: str) -> int:
    parsed = urlsplit(base_url)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"} or parsed.username or parsed.password or parsed.query or parsed.fragment:
        print("Probe requires a local HTTP application URL.")
        return 1
    settings = get_settings()
    headers = {}
    if settings.proxy_master_key:
        headers["Authorization"] = f"Bearer {settings.proxy_master_key}"
    try:
        async with httpx.AsyncClient(trust_env=False, follow_redirects=False, timeout=25) as client:
            response = await client.post(base_url.rstrip("/") + "/api/admin/providers/validate", json={"provider_id": provider_id}, headers=headers)
        if response.status_code != 200:
            print(json.dumps({"probe": "failed", "http_status": response.status_code}))
            return 1
        report = ProviderValidationReport.model_validate(response.json())
    except Exception:
        # A transport/parse/config error may contain local credentials or URL data.
        print(json.dumps({"probe": "failed", "reason": "transport_or_report_error"}))
        return 1
    # Do not echo identifiers, messages, bodies or generated text. Only schema-safe
    # names/statuses, bounded status codes, counts and timings leave this process.
    allowed_codes = {
        None, "manual_catalog", "previous_check_failed", "missing_credentials", "invalid_configuration",
        "invalid_catalog", "no_eligible_models", "model_not_eligible", "invalid_completion", "timeout",
        "response_too_large", "connection_error", "upstream_auth_error", "rate_limited",
        "upstream_unavailable", "upstream_http_error",
    }
    summary = {
        "valid": report.valid, "eligible_model_count": report.eligible_model_count,
        "total_duration_ms": round(report.total_duration_ms, 2),
        "checks": [{
            "name": check.name, "status": check.status,
            "code": check.code if check.code in allowed_codes else "unknown",
            "http_status": check.http_status,
            "duration_ms": round(check.duration_ms, 2),
        } for check in report.checks],
    }
    print(json.dumps(summary, allow_nan=False))
    return 0 if report.valid else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--provider-id", default="openrouter")
    args = parser.parse_args()
    try:
        return asyncio.run(probe(args.base_url, args.provider_id))
    except Exception:
        print(json.dumps({"probe": "failed", "reason": "configuration_or_report_error"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
