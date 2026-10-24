"""Shared task HTTP auth/redaction helpers; no provider input enters errors."""
import hmac
import uuid
from fastapi.responses import JSONResponse


def request_id(request, registry):
    value = (request.headers.get("X-Request-ID") or "").strip()
    return safe_request_id(value, registry)


def safe_request_id(value, registry):
    if (not value or len(value) > 128 or not value.isascii()
            or any(ord(c) < 32 or ord(c) == 127 for c in value)
            or registry.is_private_identifier(value)):
        for _ in range(16):
            replacement = str(uuid.uuid4())
            if not registry.is_private_identifier(replacement):
                return replacement
        return ""
    return value


def error(status, code, rid):
    return JSONResponse(status_code=status, content={"error": {
        "message": "Unsupported free request profile." if status == 400 else "Task request unavailable.",
        "type": "invalid_request_error" if status in {400, 401, 404, 413} else "server_error", "code": code}},
        headers={"X-Request-ID": rid})


def authenticated(request, registry):
    key = registry.settings.proxy_master_key
    value = (request.headers.get("Authorization") or "").strip()
    return not key or hmac.compare_digest(value.encode("utf-8"), ("Bearer " + key).encode("utf-8"))


def query_task(request, allowed, default):
    values = request.query_params.getlist("task")
    if set(request.query_params) - {"task"} or len(values) > 1:
        return None
    value = values[0] if values else default
    return value if value in allowed else None
