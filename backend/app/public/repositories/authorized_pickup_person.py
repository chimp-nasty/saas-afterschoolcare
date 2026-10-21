from datetime import datetime
from uuid import UUID

from sqlalchemy import case, func, select

from app.db.repository import Repository
from app.db.models import AuthorizedPickupPerson
from app.public.schemas.enums import PickupRelation


class AuthorizedPickupPersonRepository(Repository):
    """
    The ID check and approval are set only by staff, and PIN fields only by
    public.issue_pickup_pin() (schema/0004); nothing here writes them.
    """

    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        first_name: str,
        last_name: str,
        phone: str,
        email: str,
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
            email=email,
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

    def get_account_holder(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> AuthorizedPickupPerson | None:
        return (
            self.db.query(AuthorizedPickupPerson)
            .filter(
                AuthorizedPickupPerson.user_id == user_id,
                AuthorizedPickupPerson.location_id == location_id,
                AuthorizedPickupPerson.relation == PickupRelation.ACCOUNT_HOLDER,
                AuthorizedPickupPerson.is_active,
            )
            .first()
        )

    def issue_pin(
        self,
        *,
        person: AuthorizedPickupPerson,
    ) -> str:
        """
        A new random PIN for the person (its hash stored, to be changed at
        the next kiosk login). Returns it once, to email; it isn't kept.
        """
        pin = self.db.execute(
            select(func.public.issue_pickup_pin(person.id))
        ).scalar_one()

        self.db.refresh(person)

        return pin

    def record_identity_check(
        self,
        *,
        person: AuthorizedPickupPerson,
        staff_user_id: UUID,
        id_seen: bool,
    ) -> AuthorizedPickupPerson:
        """
        Photo ID seen (which also approves them), or approved without ID.
        Only takes effect at the staff kiosk (trg_authorized_pickup_persons_rules
        ignores it from any other session). Already-approved people are left
        as they are. Stamped with the database's clock, like the sign-outs
        it's compared with (collector_id_sighted).
        """
        now = func.now()

        if id_seen and person.identity_verified_at is None:
            person.identity_verified_at = now
            person.identity_verified_by_user_id = staff_user_id
        elif not id_seen and person.staff_approved_at is None:
            person.staff_approved_at = now
            person.staff_approved_by_user_id = staff_user_id

        self.db.flush()
        self.db.refresh(person)

        return person

    def list_for_families(
        self,
        *,
        user_ids: list[UUID],
        location_id: UUID,
    ) -> list[AuthorizedPickupPerson]:
        """These families' active pickup lists at the location (staff: RLS shows the location's)."""
        if not user_ids:
            return []

        return (
            self.db.query(AuthorizedPickupPerson)
            .filter(
                AuthorizedPickupPerson.user_id.in_(user_ids),
                AuthorizedPickupPerson.location_id == location_id,
                AuthorizedPickupPerson.is_active,
            )
            .order_by(
                case(
                    (AuthorizedPickupPerson.relation == PickupRelation.ACCOUNT_HOLDER, 0),
                    else_=1,
                ),
                AuthorizedPickupPerson.first_name,
                AuthorizedPickupPerson.last_name,
            )
            .all()
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
