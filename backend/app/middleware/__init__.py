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
            "/api/v1/auth/login": (10, 60),
            "/api/v1/auth/login/": (10, 60),
            "/api/v1/auth/register": (5, 60),
            "/api/v1/auth/register/": (5, 60),
            "/api/v1/auth/request/password-reset": (5, 60),
            "/api/v1/auth/request/password-reset/": (5, 60),
            "/api/v1/auth/reset-password": (10, 60),
            "/api/v1/auth/reset-password/": (10, 60),
        },
        exempt_paths={
            "/api/v1/webhooks/stripe",
            "/api/v1/webhooks/stripe/",
        },
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
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