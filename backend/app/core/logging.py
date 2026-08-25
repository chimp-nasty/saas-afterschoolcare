import logging
import sys
from contextvars import ContextVar


request_context: ContextVar[str] = ContextVar(
    "request_context",
    default="-",
)

tenant_context: ContextVar[str] = ContextVar(
    "tenant_context",
    default="-",
)

user_context: ContextVar[str] = ContextVar(
    "user_context",
    default="-",
)


LOG_FIELDS = [
    "request",
    "tenant_id",
    "user_id",
    "event",
    "result",
    "reason",
]


class ContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.short_name = record.name.removeprefix("app.")

        context_fields = {
            "request": request_context.get(),
            "tenant_id": tenant_context.get(),
            "user_id": user_context.get(),
        }

        for field, value in context_fields.items():
            if not hasattr(record, field):
                setattr(record, field, value)

        for field in ("event", "result", "reason"):
            if not hasattr(record, field):
                setattr(record, field, "-")

        return True


def build_formatter() -> logging.Formatter:
    context = " | ".join(
        f"{field}=%({field})s"
        for field in LOG_FIELDS
    )

    return logging.Formatter(
        (
            "%(asctime)s | "
            "%(levelname)-8s | "
            "%(short_name)s | "
            f"{context} | "
            "%(message)s"
        ),
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def build_handler() -> logging.StreamHandler:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(build_formatter())
    handler.addFilter(ContextFilter())

    return handler


def configure_logging(
    level: int = logging.INFO,
) -> None:
    handler = build_handler()

    logging.basicConfig(
        level=level,
        handlers=[handler],
        force=True,
    )

    for logger_name in (
        "uvicorn",
        "uvicorn.error",
        "uvicorn.access",
    ):
        logger = logging.getLogger(logger_name)
        logger.handlers = [handler]
        logger.setLevel(level)
        logger.propagate = False


def set_auth_context(
    *,
    tenant_id: str,
    user_id: str,
) -> tuple:
    tenant_token = tenant_context.set(tenant_id)
    user_token = user_context.set(user_id)

    return tenant_token, user_token


def reset_auth_context(
    tenant_token,
    user_token,
) -> None:
    tenant_context.reset(tenant_token)
    user_context.reset(user_token)