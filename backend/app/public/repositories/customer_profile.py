from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.customer_profile import CustomerProfile
from app.public.schemas.enums import AustralianState

class CustomerProfileRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        user_id: UUID,
        phone: str | None = None,
        address_line_1: str | None = None,
        address_line_2: str | None = None,
        suburb: str | None = None,
        state: AustralianState | None = None,
        postcode: str | None = None,
    ) -> CustomerProfile:
        record = CustomerProfile(
            user_id=user_id,
            phone=phone,
            address_line_1=address_line_1,
            address_line_2=address_line_2,
            suburb=suburb,
            state=state,
            postcode=postcode,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> CustomerProfile | None:
        return (
            self.db.query(CustomerProfile)
            .filter(CustomerProfile.id == id)
            .first()
        )

    def get_by_user_id(
        self,
        *,
        user_id: UUID,
    ) -> CustomerProfile | None:
        return (
            self.db.query(CustomerProfile)
            .filter(CustomerProfile.user_id == user_id)
            .first()
        )

    def update(
        self,
        *,
        profile: CustomerProfile,
        fields: dict,
    ) -> None:
        for field, value in fields.items():
            setattr(profile, field, value)

    def get_missing_profile_fields(
        self,
        *,
        profile: CustomerProfile,
    ) -> list[str]:
        missing_fields = []

        if not profile.phone:
            missing_fields.append("phone")

        if not profile.address_line_1:
            missing_fields.append("address_line_1")

        if not profile.suburb:
            missing_fields.append("suburb")

        if not profile.state:
            missing_fields.append("state")

        if not profile.postcode:
            missing_fields.append("postcode")

        return missing_fields