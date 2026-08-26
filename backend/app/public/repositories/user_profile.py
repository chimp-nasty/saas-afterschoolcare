from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.user_profile import UserProfile


class UserProfileRepository:
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
        state: str | None = None,
        postcode: str | None = None,
    ) -> UserProfile:
        record = UserProfile(
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
    ) -> UserProfile | None:
        return (
            self.db.query(UserProfile)
            .filter(UserProfile.id == id)
            .first()
        )
