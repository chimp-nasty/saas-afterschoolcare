from fastapi import FastAPI

from app.middleware.request_handler import RequestContextMiddleware
from app.middleware.error_handler import UnhandledExceptionMiddleware
from app.middleware.rate_limit import InMemoryRateLimitMiddleware
from app.middleware.same_origin import SameOriginMiddleware


# Called by Stripe, SES and Cloud Scheduler (the domain check), not
# browsers: no rate limit, no Origin.
WEBHOOK_PATHS = {
    "/api/v1/webhooks/stripe",
    "/api/v1/webhooks/stripe/",
    "/api/v1/webhooks/stripe/connect",
    "/api/v1/webhooks/stripe/connect/",
    "/api/v1/webhooks/ses",
    "/api/v1/webhooks/ses/",
    "/api/internal/v1/domain-check",
    "/api/internal/v1/domain-check/",
}


def configure_middleware(app: FastAPI) -> None:
    app.add_middleware(
        RequestContextMiddleware,
    )

    app.add_middleware(
        InMemoryRateLimitMiddleware,
        default_limit=180,
        default_window_seconds=60,
        # Full-path matches against the routes in app/api/router.py (served
        # under /api).
        route_limits={
            r"/api/auth/v1/login/[^/]+/?": (10, 60),
            r"/api/auth/v1/business/login/?": (10, 60),
            r"/api/platform/v1/login/?": (10, 60),
            r"/api/registration/v1/.*": (10, 60),
            r"/api/customer/v1/onboard/[^/]+/?": (5, 60),
            r"/api/auth/v1/forgot-password/[^/]+/?": (5, 60),
            r"/api/auth/v1/reset-password/?": (10, 60),
            # Setting a staff PIN checks a password.
            r"/api/staff-pin/v1/?": (10, 60),
            # Changing your password checks the current one.
            r"/api/account/v1/password/?": (10, 60),
            # Setup codes: slow down guessing.
            r"/api/kiosk/v1/[^/]+/pair/?": (10, 60),
            # Everyone at a centre uses one tablet (one IP), so the kiosk
            # gets a tablet-sized allowance per endpoint instead of the
            # per-person limits; PIN locks and the forgot-PIN spacing are
            # in the database.
            r"/api/(staff-)?kiosk/v1/.*": (300, 60),
        },
        exempt_paths=WEBHOOK_PATHS,
    )

    app.add_middleware(
        SameOriginMiddleware,
        exempt_paths=WEBHOOK_PATHS,
    )

    app.add_middleware(
        UnhandledExceptionMiddleware,
    )