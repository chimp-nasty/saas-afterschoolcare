import logging
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.response import ApiResponse
from app.errors.base import ApplicationError


logger = logging.getLogger("app.error")


def exception_response(
    msg: str,
    *,
    status_code: int = status.HTTP_400_BAD_REQUEST,
    data: Any | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content=ApiResponse[Any](
            ok=False,
            msg=msg,
            data=data,
        ).model_dump(),
    )


class UnhandledExceptionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            return await call_next(request)

        except Exception as exc:
            logger.exception(
                "Unhandled exception",
                extra={
                    "event": "unhandled_exception",
                    "result": "failed",
                    "reason": f"{type(exc).__name__}: {exc}",
                },
            )

            return exception_response(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                msg="Internal server error",
            )


class ExceptionHandlerRegistry:
    @staticmethod
    async def application_error(
        request: Request,
        exc: ApplicationError,
    ) -> JSONResponse:
        logger.warning(
            exc.message,
            extra={
                "event": exc.event,
                "result": exc.result,
                "reason": exc.log_reason or "-",
            },
        )

        return exception_response(
            status_code=exc.status_code,
            msg=exc.message,
        )

    @staticmethod
    async def http_exception(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        logger.warning(
            str(exc.detail),
            extra={
                "event": "http_exception",
                "result": "failed",
                "reason": str(exc.detail),
            },
        )

        return exception_response(
            status_code=exc.status_code,
            msg=str(exc.detail),
        )

    @staticmethod
    async def validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        errors = [
            {
                "field": ".".join(map(str, error["loc"][1:])),
                "message": error["msg"],
            }
            for error in exc.errors()
        ]

        logger.warning(
            "Request validation failed",
            extra={
                "event": "request_validation_error",
                "result": "failed",
                "reason": str(errors),
            },
        )

        return exception_response(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            msg="Request validation failed",
            data=errors,
        )

    @classmethod
    def register(cls, app: FastAPI) -> None:
        app.add_exception_handler(
            ApplicationError,
            cls.application_error,
        )

        app.add_exception_handler(
            HTTPException,
            cls.http_exception,
        )

        app.add_exception_handler(
            RequestValidationError,
            cls.validation_error,
        )