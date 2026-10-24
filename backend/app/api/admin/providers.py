"""Provider validation endpoint with authentication before body parsing."""
import hmac

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.app.config import get_settings
from backend.app.core.providers.validation import ProviderNotFound, ProviderValidationService
from backend.app.core.providers.validation_models import ProviderValidationReport, ProviderValidationRequest

router = APIRouter(prefix="/providers", tags=["Admin Providers"])


def _error(status: int, message: str) -> JSONResponse:
    return JSONResponse(status_code=status, content={
        "error": {"message": message, "type": "invalid_request_error", "code": status},
    })


@router.post("/validate", response_model=ProviderValidationReport)
async def validate_provider(request: Request):
    """Validate without enabling a provider or storing a supplied key."""
    master_key = get_settings().proxy_master_key
    if master_key:
        supplied = request.headers.get("authorization", "").strip().encode("utf-8")
        expected = f"Bearer {master_key}".encode("utf-8")
        if not hmac.compare_digest(supplied, expected):
            return _error(401, "Incorrect API key provided.")
    try:
        body = await request.json()
        validation_request = ProviderValidationRequest.model_validate(body)
    except (ValueError, ValidationError, RecursionError):
        return _error(422, "Invalid provider validation request.")
    try:
        return await ProviderValidationService().validate(validation_request)
    except ProviderNotFound:
        return _error(404, "Provider not found.")
