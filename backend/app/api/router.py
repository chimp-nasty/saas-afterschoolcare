from fastapi import APIRouter

from app.auth.routes.auth import router as auth_router
from app.tenancy.routes.location_branding import router as location_branding_router


api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(location_branding_router)