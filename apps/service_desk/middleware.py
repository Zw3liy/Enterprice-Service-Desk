"""HTTP middleware for request logging and audit context."""

from __future__ import annotations

import logging
import threading
import time
import uuid
from typing import Callable

from django.http import HttpRequest, HttpResponse

logger = logging.getLogger(__name__)

_thread_local = threading.local()


def get_current_request() -> HttpRequest | None:
    return getattr(_thread_local, "request", None)


def get_client_ip(request: HttpRequest | None) -> str | None:
    if request is None:
        return None
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


class RequestLoggingMiddleware:
    """Attach a request ID and log slow/error responses."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.request_id = request_id  # type: ignore[attr-defined]
        started = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - started) * 1000
        response["X-Request-ID"] = request_id
        if duration_ms > 1000 or response.status_code >= 500:
            logger.warning(
                "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
                request_id,
                request.method,
                request.path,
                response.status_code,
                duration_ms,
            )
        return response


class AuditContextMiddleware:
    """Expose the current request on thread-local storage for audit logging."""

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        _thread_local.request = request
        try:
            return self.get_response(request)
        finally:
            _thread_local.request = None
