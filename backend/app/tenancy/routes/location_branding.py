from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.response import ApiResponse
from app.dependencies.auth import resolve_location_id
from app.dependencies.db import get_db
from app.core.cache.cache import cached
from app.core.cache.stores import cache_stores

from app.tenancy.services.location_branding import LocationBrandingService
from app.tenancy.schemas.location_branding import PublicLocationResponse


router = APIRouter(
    prefix="/location-branding/v1",
    tags=["location-branding"],
)


@router.get("/public/{location_code}")
@cached(
    cache=cache_stores.location_branding,
    key_by="location_id",
)
def get_public_branding(
    location_id: UUID = Depends(
        resolve_location_id,
    ),
    db: Session = Depends(get_db),
) -> ApiResponse[PublicLocationResponse]:
    branding = LocationBrandingService(db=db).get_public_location(
        location_id=location_id,
    )

    return ApiResponse(
        ok=True,
        msg="Fetched public location data",
        data=branding,
    )