import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.middleware.request_handler import RequestContextMiddleware
from app.middleware.error_handler import UnhandledExceptionMiddleware
from app.middleware.rate_limit import InMemoryRateLimitMiddleware


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(
        RequestContextMiddleware,
    )

    app.add_middleware(
        InMemoryRateLimitMiddleware,
        default_limit=180,
        default_window_seconds=60,
        route_limits={
            r"/[^/]+/auth/v1/login/?": (10, 60),
            r"/[^/]+/auth/v1/register/?": (5, 60),
            r"/[^/]+/auth/v1/forgot-password/?": (5, 60),
            r"/[^/]+/auth/v1/reset-password/?": (10, 60),
        },
        exempt_paths={
            "/api/v1/webhooks/stripe",
            "/api/v1/webhooks/stripe/",
        },
    )

    if settings.APP_ENV == "dev":
        origin_regex = (
            rf"http://[a-z0-9-]+\."
            rf"{re.escape(settings.BASE_DOMAIN)}"
            rf"(:\d+)?"
        )
    else:
        origin_regex = (
            rf"https://[a-z0-9-]+\."
            rf"{re.escape(settings.BASE_DOMAIN)}"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=origin_regex,
        allow_credentials=True,
        allow_methods=[
            "GET",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        ],
        allow_headers=[
            "Authorization",
            "Content-Type",
        ],
    )

    app.add_middleware(
        UnhandledExceptionMiddleware,
    )