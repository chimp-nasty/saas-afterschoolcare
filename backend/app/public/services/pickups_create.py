from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.db.transaction import transactional
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.schemas.pickups import CreatePickupRequest, PickupResponse
from app.public.services.pickups_read import to_pickup_response


class CreatePickupService:
    """
    A family adding someone to their pickup list. The limit of three and the
    phone rules are enforced by the database (schema/0004).
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
    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        body: CreatePickupRequest,
    ) -> PickupResponse:
        # Both declarations were ticked (the request requires them).
        confirmed_at = datetime.now(timezone.utc)

        person = self.pickup_repository.create(
            user_id=user_id,
            location_id=location_id,
            first_name=body.first_name,
            last_name=body.last_name,
            phone=body.phone,
            relation=body.relation,
            relation_other=body.relation_other,
            consent_confirmed_at=confirmed_at,
            adult_confirmed_at=confirmed_at,
        )

        return to_pickup_response(person)
