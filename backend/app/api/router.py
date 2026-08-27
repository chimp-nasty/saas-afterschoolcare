from fastapi import APIRouter

from app.auth.routes.auth import router as auth_router


api_router = APIRouter(
    prefix="/{location_code}",
)

api_router.include_router(auth_router)