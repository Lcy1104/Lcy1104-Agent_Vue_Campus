"""
Simple in-process IP rate limit middleware.
Based on need.md: backend/app/core/rate_limit.py
"""
from time import monotonic

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.config import settings


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app):
        super().__init__(app)
        self.requests: dict[str, list[float]] = {}

    async def dispatch(self, request: Request, call_next):
        if request.url.path.startswith(("/api/", "/ws/")):
            client_ip = _client_ip(request)
            now = monotonic()
            window_start = now - 60
            hits = [hit for hit in self.requests.get(client_ip, []) if hit >= window_start]
            if len(hits) >= settings.RATE_LIMIT_PER_MINUTE:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={"detail": "请求过于频繁，请稍后再试"},
                )
            hits.append(now)
            self.requests[client_ip] = hits
        return await call_next(request)


def _client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip
    return request.client.host if request.client else "unknown"
