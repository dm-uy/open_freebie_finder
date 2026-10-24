"""Owned task catalog jobs using the existing orchestrator's semaphore/lifespan."""
import asyncio
from contextlib import aclosing
import json

import httpx

from backend.app.core.discovery.privacy import private_http
from backend.app.core.tasks.catalog import TASKS, SOURCE_PATHS, CatalogError

MAX_SOURCE_BYTES = 4 * 1024 * 1024


class TaskDiscovery:
    def __init__(self, orchestrator):
        self.owner = orchestrator
        self.registry = orchestrator.registry
        self.catalog = self.registry.tasks

    async def refresh(self, task):
        binding = self.catalog.binding(task)
        if binding is None:
            self.catalog.clear(task)
            return
        response = None
        client = None
        owned = self.owner._external_client is None
        try:
            async with self.owner._semaphore:
                async with asyncio.timeout(15):
                    client = self.owner._external_client or httpx.AsyncClient(trust_env=False, follow_redirects=False)
                    with private_http():
                        request = httpx.Request("GET", "https://openrouter.ai" + SOURCE_PATHS[task],
                            headers={"Authorization": "Bearer " + binding[2], "Accept": "application/json"},
                            extensions={"timeout": httpx.Timeout(15).as_dict()})
                        if self.catalog.binding(task) != binding:
                            raise CatalogError("source_changed")
                        response = await client.send(request, stream=True, auth=None, follow_redirects=False)
                        async with aclosing(response):
                            if response.status_code != 200:
                                raise CatalogError()
                            body = bytearray()
                            async for part in response.aiter_bytes():
                                if len(body) + len(part) > MAX_SOURCE_BYTES:
                                    raise CatalogError("response_too_large")
                                body.extend(part)
                            def pairs(items):
                                result = {}
                                for key, value in items:
                                    if key in result:
                                        raise ValueError
                                    result[key] = value
                                return result
                            def invalid(_):
                                raise ValueError
                            data = json.loads(body, object_pairs_hook=pairs, parse_constant=invalid)
                            if not self.catalog.publish(task, data, binding):
                                raise CatalogError("source_changed")
        except asyncio.CancelledError:
            self.catalog.clear(task)
            raise
        except Exception:
            # No exception text/body/source binding enters diagnostics.
            self.catalog.clear(task)
        finally:
            import anyio
            with anyio.CancelScope(shield=True), private_http():
                if response is not None:
                    await response.aclose()
                if owned and client is not None:
                    await client.aclose()

    def jobs(self):
        return [self.refresh(task) for task in TASKS]
