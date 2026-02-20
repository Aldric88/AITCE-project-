import json
import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.config import settings


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "time": int(time.time()),
        }
        if hasattr(record, "request_id"):
            payload["request_id"] = record.request_id
        return json.dumps(payload, ensure_ascii=True)


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("x-request-id") or str(uuid.uuid4())
        request.state.request_id = request_id
        started = time.time()
        response = await call_next(request)
        elapsed_ms = int((time.time() - started) * 1000)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = str(elapsed_ms)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if not settings.ENABLE_SECURITY_HEADERS:
            return response
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        if settings.APP_ENV.lower() in {"production", "prod"}:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response


def log_if_slow(logger: logging.Logger, operation: str, started_at: float, **meta):
    elapsed_ms = int((time.time() - started_at) * 1000)
    if elapsed_ms >= settings.SLOW_QUERY_THRESHOLD_MS:
        payload = " ".join(f"{k}={v}" for k, v in meta.items())
        logger.warning("slow_operation op=%s elapsed_ms=%s %s", operation, elapsed_ms, payload)
