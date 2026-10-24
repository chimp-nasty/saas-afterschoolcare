from uuid import UUID

from app.db.repository import Repository
from app.db.models import CustomerProfile
from app.public.schemas.enums import AustralianState

class CustomerProfileRepository(Repository):
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
        terms_document_id: UUID | None = None,
    ) -> CustomerProfile:
        record = CustomerProfile(
            user_id=user_id,
            terms_document_id=terms_document_id,
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

    def get_missing_fields_for_user(
        self,
        *,
        user_id: UUID,
    ) -> list[str]:
        """
        What the user still has to fill in before they can book. A user
        with no profile row at all is missing everything.
        """
        profile = self.get_by_user_id(user_id=user_id)

        return self.get_missing_profile_fields(
            profile=profile or CustomerProfile(),
        )

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

        # Exactly one emergency contact, and it's required.
        if not (
            profile.emergency_contact_name
            and profile.emergency_contact_phone
            and profile.emergency_contact_relation
        ):
            missing_fields.append("emergency_contact")

        return missing_fields