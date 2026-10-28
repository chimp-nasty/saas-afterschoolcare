from uuid import UUID

from sqlalchemy.orm import Session

from app.errors.tenancy import LocationNotFoundError
from app.tenancy.repositories.dashboard import OwnerDashboardRepository
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.schemas.dashboard import (
    DashboardAttentionResponse,
    DashboardNumbersResponse,
    OwnerDashboardResponse,
    UnrefundedPaymentResponse,
)


class OwnerDashboardService:
    """
    The business owner's dashboard (docs/owner-dashboard.md): a period's
    numbers beside the period before, what needs attention now, and the
    payments to refund in Stripe. Every number comes from the database
    (OwnerDashboardRepository), which checks the owner's permission too.
    """

    def __init__(
        self,
        *,
        db: Session,
        dashboard_repository: OwnerDashboardRepository,
        location_repository: LocationRepository,
    ):
        self.db = db
        self.dashboard_repository = dashboard_repository
        self.location_repository = location_repository

    def get(
        self,
        *,
        tenant_id: UUID,
        week: int | None,
        location_id: UUID | None,
    ) -> OwnerDashboardResponse:
        """`week`: weeks from this one (-1 last week); None for all time."""
        if location_id is not None:
            location = self.location_repository.get_by_id(id=location_id)

            if not location or location.tenant_id != tenant_id:
                raise LocationNotFoundError()

        offset = week
        args = {"tenant_id": tenant_id, "location_id": location_id}

        [first_range, *_] = self.dashboard_repository.ranges(week_offset=offset, **args) or [None]
        attention = self.dashboard_repository.attention(**args)

        return OwnerDashboardResponse(
            week=week,
            from_date=first_range.from_date if first_range else None,
            to_date=first_range.to_date if first_range else None,
            current=self._numbers(offset=offset, **args),
            previous=self._numbers(offset=offset - 1, **args) if offset is not None else None,
            attention=DashboardAttentionResponse(
                reviews_pending=attention.reviews_pending,
                documents_requested=attention.documents_requested,
                enquiries_new=attention.enquiries_new,
                reactivation_requests=attention.reactivation_requests,
                inactive_families=attention.inactive_families,
                unrefunded_payments=[
                    UnrefundedPaymentResponse.model_validate(row, from_attributes=True)
                    for row in self.dashboard_repository.unrefunded_payments(**args)
                ],
            ),
        )

    def _numbers(self, *, tenant_id: UUID, location_id: UUID | None, offset: int | None) -> DashboardNumbersResponse:
        row = self.dashboard_repository.period(tenant_id=tenant_id, location_id=location_id, week_offset=offset)

        # Sign-ups, refunds and cancellations haven't happened yet in a
        # future week: shown as none rather than 0.
        future = offset is not None and offset > 0

        return DashboardNumbersResponse(
            revenue_cents=row.revenue_cents,
            currency=row.currency,
            bookings=row.bookings,
            active_families=row.active_families,
            returning_families=row.returning_families,
            average_sessions=round(row.bookings / row.active_families, 1) if row.active_families else None,
            registrations=None if future else row.registrations,
            refunds=None if future else row.refunds,
            refunded_cents=None if future else row.refunded_cents,
            cancelled_unrefunded=None if future else row.cancelled_unrefunded,
        )
