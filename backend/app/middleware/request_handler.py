from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import request_context


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        value = f"{request.method} {request.url.path}"
        token = request_context.set(value)

        try:
            return await call_next(request)
        finally:
            request_context.reset(token)