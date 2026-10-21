import logging
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.errors.pickups import PickupNotFoundError
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.schemas.attendance import RollPickupPersonResponse
from app.public.services.attendance import to_pickup_person


logger = logging.getLogger("app.pickups")


class PickupIdentityService:
    """
    A staff member checking a pickup person's photo ID (which approves them)
    or approving them without ID, at the staff kiosk (docs/kiosk-procedures.md,
    section 4). Only takes effect there: trg_authorized_pickup_persons_rules
    ignores these fields from any other session, admins' included.
    """

    def __init__(
        self,
        *,
        db: Session,
        pickup_repository: AuthorizedPickupPersonRepository,
    ):
        self.db = db
        self.pickup_repository = pickup_repository

    @transactional
    def check(
        self,
        *,
        pickup_person_id: UUID,
        staff_user_id: UUID,
        id_seen: bool,
    ) -> RollPickupPersonResponse:
        person = self.pickup_repository.get_by_id(id=pickup_person_id)

        if not person or not person.is_active:
            raise PickupNotFoundError()

        person = self.pickup_repository.record_identity_check(
            person=person,
            staff_user_id=staff_user_id,
            id_seen=id_seen,
        )

        logger.info(
            "Pickup person approved",
            extra={
                "event": "pickup_id_checked" if id_seen else "pickup_approved_without_id",
                "result": "success",
                "reason": f"pickup_person_id={pickup_person_id}",
            },
        )

        return to_pickup_person(person)
