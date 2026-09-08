from fastapi import APIRouter

# auth
from app.auth.routes.auth import router as auth_router

# tenancy
from app.tenancy.routes.location_branding import router as location_branding_router

# public
from app.public.routes.customer import router as customer_router
from app.public.routes.bookings import router as booking_router
from app.public.routes.children import router as children_router
from app.public.routes.location_service_days import router as location_service_day_router
from app.public.routes.location_services import router as location_service_router


api_router = APIRouter()

# auth
api_router.include_router(auth_router)

# tenancy
api_router.include_router(location_branding_router)

# public
api_router.include_router(customer_router)
api_router.include_router(booking_router)
api_router.include_router(children_router)
api_router.include_router(location_service_day_router)
api_router.include_router(location_service_router)