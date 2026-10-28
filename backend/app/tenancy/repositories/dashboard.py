from uuid import UUID

from sqlalchemy import Row, text

from app.db.repository import Repository


class OwnerDashboardRepository(Repository):
    """
    The owner dashboard's numbers (docs/owner-dashboard.md), from the
    public.owner_dashboard_* functions (schema/0004): they hold the
    definitions and check the owner's tenant permission themselves.
    """

    def ranges(self, *, tenant_id: UUID, location_id: UUID | None, week_offset: int | None) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.owner_dashboard_ranges(:tenant_id, :location_id, :offset)"),
            {"tenant_id": tenant_id, "location_id": location_id, "offset": week_offset},
        ).all()

    def period(self, *, tenant_id: UUID, location_id: UUID | None, week_offset: int | None) -> Row:
        return self.db.execute(
            text("SELECT * FROM public.owner_dashboard_period(:tenant_id, :location_id, :offset)"),
            {"tenant_id": tenant_id, "location_id": location_id, "offset": week_offset},
        ).one()

    def attention(self, *, tenant_id: UUID, location_id: UUID | None) -> Row:
        return self.db.execute(
            text("SELECT * FROM public.owner_dashboard_attention(:tenant_id, :location_id)"),
            {"tenant_id": tenant_id, "location_id": location_id},
        ).one()

    def unrefunded_payments(self, *, tenant_id: UUID, location_id: UUID | None) -> list[Row]:
        return self.db.execute(
            text("SELECT * FROM public.owner_dashboard_unrefunded_payments(:tenant_id, :location_id)"),
            {"tenant_id": tenant_id, "location_id": location_id},
        ).all()
