from fastapi import APIRouter

# auth
from app.auth.routes.auth import router as auth_router

# tenancy
from app.tenancy.routes.location_branding import router as location_branding_router

# public
from app.public.routes.customer import router as customer_router


api_router = APIRouter()

# auth
api_router.include_router(auth_router)

# tenancy
api_router.include_router(location_branding_router)

# public
api_router.include_router(customer_router)