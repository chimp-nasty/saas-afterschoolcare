from fastapi import APIRouter

# auth
from app.auth.routes.auth import router as auth_router
from app.auth.routes.staff_pin import router as staff_pin_router
from app.auth.routes.account import router as account_router
from app.auth.routes.staff_accounts import router as staff_accounts_router
from app.public.routes.families import router as families_router

# tenancy
from app.tenancy.routes.location_branding import router as location_branding_router
from app.tenancy.routes.stripe_account import router as stripe_account_router
from app.tenancy.routes.business import router as business_router
from app.tenancy.routes.domain_check import router as domain_check_router

# platform
from app.platform.routes.platform import router as platform_router
from app.platform.routes.registration import router as registration_router

# public
from app.public.routes.customer import router as customer_router
from app.public.routes.bookings import router as booking_router
from app.public.routes.children import router as children_router
from app.public.routes.location_service_days import router as location_service_day_router
from app.public.routes.location_services import router as location_service_router
from app.public.routes.actions import router as actions_router
from app.public.routes.pickups import router as pickups_router
from app.public.routes.refunds import router as refunds_router
from app.public.routes.child_documents import router as child_documents_router
from app.public.routes.medical_reviews import router as medical_reviews_router
from app.public.routes.kiosk_devices import router as kiosk_devices_router
from app.public.routes.attendance import router as attendance_router
from app.public.routes.payment_check import router as payment_check_router

# kiosk
from app.kiosk.routes.family_kiosk import router as family_kiosk_router
from app.kiosk.routes.staff_kiosk import router as staff_kiosk_router

# integrations
from app.integrations.payments.stripe.router import router as stripe_webhook_router
from app.integrations.email.router import router as ses_webhook_router


api_router = APIRouter()

# auth
api_router.include_router(auth_router)
api_router.include_router(staff_pin_router)
api_router.include_router(account_router)
api_router.include_router(staff_accounts_router)
api_router.include_router(families_router)

# tenancy
api_router.include_router(location_branding_router)
api_router.include_router(stripe_account_router)
api_router.include_router(business_router)
api_router.include_router(domain_check_router)

# platform
api_router.include_router(platform_router)
api_router.include_router(registration_router)

# public
api_router.include_router(customer_router)
api_router.include_router(booking_router)
api_router.include_router(children_router)
api_router.include_router(location_service_day_router)
api_router.include_router(location_service_router)
api_router.include_router(actions_router)
api_router.include_router(pickups_router)
api_router.include_router(refunds_router)
api_router.include_router(child_documents_router)
api_router.include_router(medical_reviews_router)
api_router.include_router(kiosk_devices_router)
api_router.include_router(attendance_router)
api_router.include_router(payment_check_router)

# kiosk
api_router.include_router(family_kiosk_router)
api_router.include_router(staff_kiosk_router)

# integrations
api_router.include_router(stripe_webhook_router)
api_router.include_router(ses_webhook_router)
