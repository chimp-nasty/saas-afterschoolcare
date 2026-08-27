import re
import time

from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

from app.errors.auth import LimitExceeded


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        *,
        default_limit: int = 120,
        default_window_seconds: int = 60,
        route_limits: dict[str, tuple[int, int]] | None = None,
        exempt_paths: set[str] | None = None,
    ):
        super().__init__(app)

        self.default_limit = default_limit
        self.default_window_seconds = default_window_seconds

        self.route_limits = {
            re.compile(pattern): limits
            for pattern, limits in (route_limits or {}).items()
        }

        self.exempt_paths = exempt_paths or set()

        self.requests: dict[str, deque[float]] = defaultdict(deque)

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ):
        path = request.url.path

        if request.method == "OPTIONS":
            return await call_next(request)

        if path in self.exempt_paths:
            return await call_next(request)

        limit, window_seconds = self._get_limits(path)

        client_ip = self._get_client_ip(request)
        key = f"{client_ip}:{path}"

        now = time.time()
        timestamps = self.requests[key]

        while timestamps and timestamps[0] <= now - window_seconds:
            timestamps.popleft()

        if len(timestamps) >= limit:
            raise LimitExceeded(
                action="rate_limit",
                message="Too many requests. Please try again shortly.",
                log_reason=(
                    f"path={path}; "
                    f"client_ip={client_ip}; "
                    f"limit={limit}; "
                    f"window_seconds={window_seconds}"
                ),
            )

        timestamps.append(now)

        return await call_next(request)

    def _get_limits(
        self,
        path: str,
    ) -> tuple[int, int]:
        for pattern, limits in self.route_limits.items():
            if pattern.fullmatch(path):
                return limits

        return (
            self.default_limit,
            self.default_window_seconds,
        )

    def _get_client_ip(
        self,
        request: Request,
    ) -> str:
        forwarded_for = request.headers.get(
            "x-forwarded-for",
        )

        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        if request.client:
            return request.client.host

        return "unknown"