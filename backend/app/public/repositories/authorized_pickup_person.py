from uuid import UUID

from sqlalchemy.orm import Session

from app.public.models.authorized_pickup_person import AuthorizedPickupPerson


class AuthorizedPickupPersonRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        child_id: UUID,
        user_id: UUID,
        first_name: str,
        last_name: str,
        phone: str,
        relation: str,
        consent_confirmed: bool | None = None,
        identity_verified_at=None,
        identity_verified_by_user_id: UUID | None = None,
        is_active: bool = True,
    ) -> AuthorizedPickupPerson:
        record = AuthorizedPickupPerson(
            child_id=child_id,
            user_id=user_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            relation=relation,
            consent_confirmed=consent_confirmed,
            identity_verified_at=identity_verified_at,
            identity_verified_by_user_id=identity_verified_by_user_id,
            is_active=is_active,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> AuthorizedPickupPerson | None:
        return (
            self.db.query(AuthorizedPickupPerson)
            .filter(AuthorizedPickupPerson.id == id)
            .first()
        )
