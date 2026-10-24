"""Closed task APIs. No nonchat route uses the chat alternative-model cascade."""
import asyncio
import json
import logging
import anyio
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse, Response
from backend.app.core.providers.registry import get_registry
from backend.app.core.tasks.http import authenticated, error, request_id, safe_request_id
from backend.app.core.tasks.protocol import parse_json, RequestError
from backend.app.core.tasks.transport import TaskExecutor, TaskError

logger = logging.getLogger(__name__)
router = APIRouter()


async def _owned_request(request, operation):
    work = asyncio.create_task(operation)
    async def disconnected():
        while True:
            message = await request.receive()
            if message["type"] == "http.disconnect":
                return
    observer = asyncio.create_task(disconnected())
    try:
        done, _ = await asyncio.wait((work, observer), return_when=asyncio.FIRST_COMPLETED)
        if work in done:
            return await work
        raise TaskError(503, "client_disconnected")
    finally:
        for job in (work, observer):
            if not job.done(): job.cancel()
        with anyio.CancelScope(shield=True):
            await asyncio.gather(work, observer, return_exceptions=True)


async def _perform(task, request):
    registry = getattr(request.app.state, "provider_registry", None) or get_registry()
    rid = request_id(request, registry)
    entered = False
    try:
        if not authenticated(request, registry):
            return error(401, "authentication_error", rid)
        if request.query_params:
            return error(400, "unsupported_free_request", rid)
        body = bytearray()
        async with asyncio.timeout(30):
            async for chunk in request.stream():
                if len(body) + len(chunk) > 256 * 1024:
                    return error(413, "request_too_large", rid)
                body.extend(chunk)
            payload = parse_json(body)
            executor = getattr(request.app.state, "task_executor", None) or TaskExecutor(registry)
            entered = True
            result = await _owned_request(request, executor.execute(task, payload, rid))
            if result.media_type == "application/json":
                return JSONResponse(result.data, headers={"X-Request-ID": result.request_id})
            return Response(result.data, media_type=result.media_type, headers={"X-Request-ID": result.request_id})
    except RequestError:
        return error(400, "unsupported_free_request", safe_request_id(rid, registry))
    except TaskError as exc:
        return error(exc.status, exc.code, safe_request_id(exc.request_id or rid, registry))
    except TimeoutError:
        return error(503, "request_timeout", safe_request_id(rid, registry))
    except Exception:
        return error(503, "task_unavailable", safe_request_id(rid, registry))
    finally:
        if not entered:
            logger.info(json.dumps({"event": "task_request", "task": task, "request_id": safe_request_id(rid, registry),
                "target": None, "attempt_count": 0, "delivery": "failed", "code": "preflight_rejected"}))


@router.post("/embeddings")
async def embeddings(request: Request):
    return await _perform("embeddings", request)


@router.post("/rerank")
async def rerank(request: Request):
    return await _perform("rerank", request)


@router.post("/decisions")
async def decisions(request: Request):
    return await _perform("decisions", request)


@router.post("/audio/speech")
async def speech(request: Request):
    return await _perform("speech", request)
