from uuid import UUID

from sqlalchemy.orm import Session

from app.db.models import AuthorizedPickupPerson
from app.db.transaction import transactional
from app.integrations.email.messages import KioskPinEmail
from app.integrations.email.outbox import EmailOutbox
from app.errors.pickups import AccountHolderPickupError, PickupNotFoundError
from app.public.repositories.authorized_pickup_person import AuthorizedPickupPersonRepository
from app.public.schemas.enums import PickupRelation
from app.public.schemas.pickups import PickupResponse, UpdatePickupRequest
from app.public.services.pickups_read import to_pickup_response


# Can be changed but not cleared (NOT NULL), so an explicit null for one is
# ignored rather than failing in the database.
_REQUIRED_FIELDS = ("first_name", "last_name", "phone", "email", "relation")


class UpdatePickupService:
    """
    A family editing or removing someone on their pickup list. Resetting the
    ID check after a name or phone change, and the PIN after an email
    change, happens in the database (trg_authorized_pickup_persons_rules,
    schema/0004); a new PIN is then emailed to the new address.
    """

    def __init__(
        self,
        *,
        db: Session,
        pickup_repository: AuthorizedPickupPersonRepository,
    ):
        self.db = db
        self.pickup_repository = pickup_repository
        self.emails = EmailOutbox(db)

    @transactional
    def update(
        self,
        *,
        id: UUID,
        body: UpdatePickupRequest,
    ) -> PickupResponse:
        person = self._get_editable(id=id)

        values = {
            field: value
            for field, value in body.model_dump(exclude_unset=True).items()
            if not (field in _REQUIRED_FIELDS and value is None)
        }

        old_email = person.email

        if values:
            person = self.pickup_repository.update(
                person=person,
                values=values,
            )

        if person.email.lower() != old_email.lower():
            self.emails.queue(KioskPinEmail(
                location_id=person.location_id,
                pickup_person_id=person.id,
                to_email=person.email,
                first_name=person.first_name,
                pin=self.pickup_repository.issue_pin(person=person),
            ))

        return to_pickup_response(person)

    @transactional
    def deactivate(
        self,
        *,
        id: UUID,
    ) -> PickupResponse:
        person = self._get_editable(id=id)

        self.pickup_repository.deactivate(person=person)

        return to_pickup_response(person)

    def _get_editable(
        self,
        *,
        id: UUID,
    ) -> AuthorizedPickupPerson:
        # RLS hides other families' people, so they read as not found.
        person = self.pickup_repository.get_by_id(id=id)

        if not person or not person.is_active:
            raise PickupNotFoundError()

        # Kept in sync with the account holder's profile instead.
        if person.relation == PickupRelation.ACCOUNT_HOLDER:
            raise AccountHolderPickupError()

        return person
