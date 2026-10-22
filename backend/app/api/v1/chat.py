"""OpenAI-compatible /v1/chat/completions endpoint."""
import json
import logging
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
    content: str
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


def _verify_auth(authorization: Optional[str]) -> Optional[JSONResponse]:
    """Verify authorization against optional proxy_master_key."""
    settings = get_settings()
    if not settings.proxy_master_key:
        return None  # Permissive auth: accept any key or missing header

    expected = f"Bearer {settings.proxy_master_key}"
    if not authorization or authorization.strip() != expected:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": {
                    "message": "Incorrect API key provided.",
                    "type": "invalid_request_error",
                    "code": 401,
                }
            },
        )
    return None


@router.post("/chat/completions", tags=["OpenAI Compatible"])
async def create_chat_completion(
    request: Request,
    authorization: Optional[str] = Header(None),
) -> Any:
    """Execute chat completion with transparent cascade failover and canonical masking."""
    # 1. Permissive Authentication check
    auth_err = _verify_auth(authorization)
    if auth_err:
        return auth_err

    # 2. Parse request body
    try:
        body = await request.json()
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "message": "Invalid JSON body provided.",
                    "type": "invalid_request_error",
                    "code": 400,
                }
            },
        )

    try:
        req_payload = ChatCompletionRequest(**body)
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "error": {
                    "message": f"Validation error: {exc}",
                    "type": "invalid_request_error",
                    "code": 400,
                }
            },
        )

    requested_model = req_payload.model.strip()
    cascade_router = get_cascade_router()

    # 3. Verify candidate availability (404 if model completely unknown and no candidates)
    candidates = cascade_router.resolve_candidates(requested_model)
    if not candidates:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "error": {
                    "message": f"The model '{requested_model}' does not exist or has no active free providers.",
                    "type": "invalid_request_error",
                    "code": 404,
                }
            },
        )

    # 4. Route Execution: Streaming vs Buffered
    try:
        if req_payload.stream:
            stream_gen = await cascade_router.route_stream_completion(
                requested_model=requested_model,
                payload=body,
            )
            return StreamingResponse(
                stream_gen,
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            response_data = await cascade_router.route_completion(
                requested_model=requested_model,
                payload=body,
            )
            return JSONResponse(status_code=status.HTTP_200_OK, content=response_data)

    except UpstreamProviderError as exc:
        logger.error("All pool candidates exhausted: %s", str(exc))
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "error": {
                    "message": str(exc),
                    "type": "service_unavailable",
                    "code": 503,
                }
            },
        )
    except Exception as exc:
        logger.exception("Unexpected error in chat completion: %s", str(exc))
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": {
                    "message": f"Internal proxy error: {str(exc)}",
                    "type": "api_error",
                    "code": 500,
                }
            },
        )
