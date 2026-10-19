from datetime import datetime
from uuid import UUID

from sqlalchemy import case

from app.db.repository import Repository
from app.db.models import AuthorizedPickupPerson
from app.public.schemas.enums import PickupRelation


class AuthorizedPickupPersonRepository(Repository):
    """
    The ID check and kiosk fields are set only by staff and the database
    (schema/0004); nothing here writes them.
    """

    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        first_name: str,
        last_name: str,
        phone: str,
        relation: PickupRelation,
        relation_other: str | None,
        consent_confirmed_at: datetime,
        adult_confirmed_at: datetime,
    ) -> AuthorizedPickupPerson:
        record = AuthorizedPickupPerson(
            user_id=user_id,
            location_id=location_id,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            relation=relation,
            relation_other=relation_other,
            consent_confirmed_at=consent_confirmed_at,
            adult_confirmed_at=adult_confirmed_at,
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

    def list_active(self) -> list[AuthorizedPickupPerson]:
        """The active list RLS lets the user see: account holder first."""
        return (
            self.db.query(AuthorizedPickupPerson)
            .filter(AuthorizedPickupPerson.is_active)
            .order_by(
                case(
                    (AuthorizedPickupPerson.relation == PickupRelation.ACCOUNT_HOLDER, 0),
                    else_=1,
                ),
                AuthorizedPickupPerson.created_at.asc(),
            )
            .all()
        )

    def update(
        self,
        *,
        person: AuthorizedPickupPerson,
        values: dict,
    ) -> AuthorizedPickupPerson:
        for field, value in values.items():
            setattr(person, field, value)

        self.db.flush()

        # The rules trigger may have reset the ID check or PIN.
        self.db.refresh(person)

        return person

    def deactivate(
        self,
        *,
        person: AuthorizedPickupPerson,
    ) -> AuthorizedPickupPerson:
        person.is_active = False

        self.db.flush()

        return person
