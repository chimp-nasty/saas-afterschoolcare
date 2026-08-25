from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import configure_logging
from app.middleware import configure_middleware
from app.middleware.error_handler import ExceptionHandlerRegistry


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI()

    configure_middleware(app)

    app.include_router(api_router)

    ExceptionHandlerRegistry.register(app)

    return app


app = create_app()