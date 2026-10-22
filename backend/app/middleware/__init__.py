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
        # Full-path matches against the routes in app/api/router.py.
        route_limits={
            r"/auth/v1/login/[^/]+/?": (10, 60),
            r"/customer/v1/onboard/[^/]+/?": (5, 60),
            r"/auth/v1/forgot-password/[^/]+/?": (5, 60),
            r"/auth/v1/reset-password/?": (10, 60),
            # Setting a staff PIN checks a password.
            r"/staff-pin/v1/?": (10, 60),
            # Changing your password checks the current one.
            r"/account/v1/password/?": (10, 60),
            # Setup codes: slow down guessing.
            r"/kiosk/v1/[^/]+/pair/?": (10, 60),
            # Everyone at a centre uses one tablet (one IP), so the kiosk
            # gets a tablet-sized allowance per endpoint instead of the
            # per-person limits; PIN locks and the forgot-PIN spacing are
            # in the database.
            r"/(staff-)?kiosk/v1/.*": (300, 60),
        },
        exempt_paths={
            "/api/v1/webhooks/stripe",
            "/api/v1/webhooks/stripe/",
            "/api/v1/webhooks/stripe/connect",
            "/api/v1/webhooks/stripe/connect/",
            "/api/v1/webhooks/ses",
            "/api/v1/webhooks/ses/",
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
            # The family kiosk's per-person session token (app/kiosk/tokens.py).
            "X-Kiosk-Session",
            # The staff kiosk's staff member and PIN, sent with each action
            # (app/kiosk/dependencies.py).
            "X-Kiosk-Staff",
            "X-Kiosk-Pin",
        ],
    )

    app.add_middleware(
        UnhandledExceptionMiddleware,
    )