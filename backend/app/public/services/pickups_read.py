from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AuthorizedPickupPerson
from app.errors.pickups import PickupNotFoundError
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.schemas.enums import PickupRelation
from app.public.schemas.pickups import PickupResponse


def to_pickup_response(person: AuthorizedPickupPerson) -> PickupResponse:
    return PickupResponse(
        id=person.id,
        first_name=person.first_name,
        last_name=person.last_name,
        phone=person.phone,
        relation=person.relation,
        relation_other=person.relation_other,
        is_account_holder=person.relation == PickupRelation.ACCOUNT_HOLDER,
        identity_verified=person.identity_verified_at is not None,
        kiosk_pin_set=person.pin_hash is not None,
        created_at=person.created_at,
    )


class ReadPickupService:
    def __init__(
        self,
        *,
        db: Session,
        pickup_repository: AuthorizedPickupPersonRepository,
    ):
        self.db = db
        self.pickup_repository = pickup_repository

    def list_active(self) -> list[PickupResponse]:
        # RLS limits a customer to their own family's list.
        return [
            to_pickup_response(person)
            for person in self.pickup_repository.list_active()
        ]

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> PickupResponse:
        person = self.pickup_repository.get_by_id(id=id)

        if not person or not person.is_active:
            raise PickupNotFoundError()

        return to_pickup_response(person)
