"""OpenAI-compatible /v1/chat/completions endpoint with correlation tracing."""
import hmac
import json
import logging
import uuid
from typing import Any, Optional
from fastapi import APIRouter, Header, Request, status
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from backend.app.config import get_settings
from backend.app.core.adapters.openai_client import UpstreamProviderError
from backend.app.core.balancer.router import CascadeRouter
from backend.app.core.providers.registry import get_registry

logger = logging.getLogger(__name__)
router = APIRouter()


class ChatMessage(BaseModel):
    """Chat message object conforming to OpenAI schema."""

    role: str
    content: Any
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    """Chat completion request payload conforming to OpenAI schema."""

    model: str
    messages: list[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    top_p: Optional[float] = None
    presence_penalty: Optional[float] = None
    frequency_penalty: Optional[float] = None
    stop: Optional[Any] = None

    model_config = {"extra": "allow"}


# Module-level router instance
_cascade_router: Optional[CascadeRouter] = None


def get_cascade_router() -> CascadeRouter:
    """Return CascadeRouter singleton."""
    global _cascade_router
    if _cascade_router is None:
        _cascade_router = CascadeRouter(registry=get_registry())
    return _cascade_router


def _json_response(status_code: int, content: dict[str, Any], request_id: str) -> JSONResponse:
    """Emit JSONResponse with mandatory X-Request-ID header reflection (BR-2, AC-2, AC-3, AC-4)."""
    return JSONResponse(
        status_code=status_code,
        content=content,
        headers={"X-Request-ID": request_id},
    )


def _verify_auth(authorization: Optional[str], request_id: str) -> Optional[JSONResponse]:
    """Verify authorization against optional proxy_master_key using constant-time comparison."""
    settings = get_settings()
    if not settings.proxy_master_key:
        return None  # Permissive auth: accept any key or missing header

    expected = f"Bearer {settings.proxy_master_key}"
    if not authorization or not hmac.compare_digest(authorization.strip(), expected):
        return _json_response(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": "Incorrect API key provided.",
                    "type": "invalid_request_error",
                    "code": 401,
                }
            },
            request_id=request_id,
        )
    return None


@router.post("/chat/completions", tags=["OpenAI Compatible"])
async def create_chat_completion(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Any:
    """Execute chat completion with transparent cascade failover, canonical masking, and correlation tracing."""
    # Ingest incoming correlation ID or generate fresh UUID4 (BR-2, AC-2, AC-3)
    raw_corr_id = request.headers.get("X-Request-ID")
    request_id = raw_corr_id.strip() if raw_corr_id and raw_corr_id.strip() else str(uuid.uuid4())

    # 1. Permissive Authentication check
    auth_err = _verify_auth(authorization, request_id)
    if auth_err:
        return auth_err

    # 2. Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return _json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "message": "Invalid JSON body provided.",
                    "type": "invalid_request_error",
                    "code": 400,
                }
            },
            request_id=request_id,
        )

    try:
        req_payload = ChatCompletionRequest(**body)
    except Exception as exc:
        return _json_response(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "message": f"Validation error: {exc}",
                    "type": "invalid_request_error",
                    "code": 400,
                }
            },
            request_id=request_id,
        )

    requested_model = req_payload.model.strip()
    cascade_router = get_cascade_router()

    # 3. Verify candidate availability (404 if model completely unknown and no candidates)
    candidates = cascade_router.resolve_candidates(requested_model)
    if not candidates:
        return _json_response(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "message": f"The model '{requested_model}' does not exist or has no active free providers.",
                    "type": "invalid_request_error",
                    "code": 404,
                }
            },
            request_id=request_id,
        )

    # 4. Route Execution: Streaming vs Buffered
    try:
        if req_payload.stream:
            stream_gen = await cascade_router.route_stream_completion(
                requested_model=requested_model,
                payload=body,
                request_id=request_id,
            )
            return StreamingResponse(
                stream_gen,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                    "X-Request-ID": request_id,
                },
            )
        else:
            response_data = await cascade_router.route_completion(
                requested_model=requested_model,
                payload=body,
                request_id=request_id,
            )
            return _json_response(
                status_code=status.HTTP_200_OK,
                content=response_data,
                request_id=request_id,
            )

    except UpstreamProviderError as exc:
        logger.error("All pool candidates exhausted: %s", str(exc))
        return _json_response(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "message": str(exc),
                    "type": "service_unavailable",
                    "code": 503,
                }
            },
            request_id=request_id,
        )
    except Exception as exc:
        logger.exception("Unexpected error in chat completion: %s", str(exc))
        return _json_response(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": f"Internal proxy error: {str(exc)}",
                    "type": "api_error",
                    "code": 500,
                }
            },
            request_id=request_id,
        )
