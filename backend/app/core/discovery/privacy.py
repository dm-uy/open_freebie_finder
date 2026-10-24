"""Task-local suppression of HTTP library diagnostics containing private headers."""
import logging
from contextlib import contextmanager
from contextvars import ContextVar

_private = ContextVar("private_provider_http", default=False)


class _Filter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not _private.get()


for _name in ("httpx", "httpcore.connection", "httpcore.http11", "httpcore.http2", "httpcore.proxy", "httpcore.socks"):
    logging.getLogger(_name).addFilter(_Filter())


@contextmanager
def private_http():
    token = _private.set(True)
    try:
        yield
    finally:
        _private.reset(token)
