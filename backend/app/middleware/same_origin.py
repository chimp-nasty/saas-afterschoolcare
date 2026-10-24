import logging

from collections.abc import Callable
from urllib.parse import urlsplit

from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware

from app.middleware.error_handler import exception_response


logger = logging.getLogger("app.error")


SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


class SameOriginMiddleware(BaseHTTPMiddleware):
    """
    Refuses changes (POST, PUT, PATCH, DELETE) sent from another site.

    The API is served on each tenant's own site under /api, so a browser's
    request carries an Origin matching its Host. SvelteKit's own check
    doesn't cover the API (pages are ssr = false). Webhooks come from Stripe
    and SES without an Origin, so their paths are exempt.
    """

    def __init__(
        self,
        app,
        *,
        exempt_paths: set[str] | None = None,
    ):
        super().__init__(app)

        self.exempt_paths = exempt_paths or set()

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ):
        if (
            request.method in SAFE_METHODS
            or request.url.path in self.exempt_paths
        ):
            return await call_next(request)

        origin = request.headers.get("origin")
        host = request.headers.get("host")

        if (
            not origin
            or not host
            or urlsplit(origin).netloc.lower() != host.lower()
        ):
            # Exceptions raised in middleware skip the app's exception
            # handlers (they'd surface as a 500), so respond directly.
            logger.warning(
                "Cross-site request refused",
                extra={
                    "event": "same_origin",
                    "result": "refused",
                    "reason": (
                        f"path={request.url.path}; "
                        f"origin={origin}; "
                        f"host={host}"
                    ),
                },
            )

            return exception_response(
                "This request didn't come from this site.",
                status_code=status.HTTP_403_FORBIDDEN,
            )

        return await call_next(request)
