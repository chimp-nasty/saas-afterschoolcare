from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.logging import configure_logging
from app.db.session import assert_rls_enforced
from app.middleware import configure_middleware
from app.middleware.error_handler import ExceptionHandlerRegistry


@asynccontextmanager
async def lifespan(app: FastAPI):
    assert_rls_enforced()
    yield


def create_app() -> FastAPI:
    configure_logging()

    app = FastAPI(lifespan=lifespan)

    configure_middleware(app)

    app.include_router(api_router)

    ExceptionHandlerRegistry.register(app)

    return app


app = create_app()
