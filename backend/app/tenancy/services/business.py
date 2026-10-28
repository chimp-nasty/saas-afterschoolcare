import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.cache.stores import cache_stores
from app.db.transaction import transactional
from app.errors.tenancy import LocationNotFoundError
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.repositories.stripe_account import TenantStripeAccountRepository
from app.tenancy.repositories.tenant import TenantRepository
from app.tenancy.schemas.business import (
    BusinessLocationRequest,
    BusinessLocationResponse,
    BusinessOverviewResponse,
    BusinessSettingsRequest,
    BusinessSettingsResponse,
)


logger = logging.getLogger("app.tenancy")


def _to_location(location, services_offered: int) -> BusinessLocationResponse:
    return BusinessLocationResponse(
        id=location.id,
        code=location.code,
        name=location.name,
        address_line_1=location.address_line_1,
        address_line_2=location.address_line_2,
        suburb=location.suburb,
        state=location.state,
        postcode=location.postcode,
        phone=location.phone,
        email=location.email,
        timezone=location.timezone,
        enquiry_notice_email=location.enquiry_notice_email,
        services_offered=services_offered,
    )


class BusinessService:
    """
    Business settings (/business, docs/tenant-administration.md): the
    tenant's owner runs the whole business here (its details and its
    locations; Stripe is StripeConnectService). Each route checks the
    tenant permission; RLS checks it again on every write
    (auth.has_tenant_permission).
    """

    def __init__(
        self,
        *,
        db: Session,
        tenant_repository: TenantRepository,
        location_repository: LocationRepository,
        stripe_account_repository: TenantStripeAccountRepository,
    ):
        self.db = db
        self.tenant_repository = tenant_repository
        self.location_repository = location_repository
        self.stripe_account_repository = stripe_account_repository

    def overview(
        self,
        *,
        tenant_id: UUID,
    ) -> BusinessOverviewResponse:
        """What's set up and what isn't: the first page of Business settings."""
        tenant = self.tenant_repository.get_by_id(id=tenant_id)
        account = self.stripe_account_repository.get_for_tenant(tenant_id=tenant_id)
        takes_payments = self.db.execute(
            select(func.tenancy.tenant_payments_account(tenant_id))
        ).scalar() is not None

        return BusinessOverviewResponse(
            name=tenant.name,
            details_complete=all((tenant.legal_name, tenant.abn, tenant.email, tenant.phone)),
            locations=self.list_locations(tenant_id=tenant_id),
            payments_connected=account is not None,
            takes_payments=takes_payments,
        )

    def get_settings(
        self,
        *,
        tenant_id: UUID,
    ) -> BusinessSettingsResponse:
        return BusinessSettingsResponse.model_validate(
            self.tenant_repository.get_by_id(id=tenant_id),
        )

    @transactional
    def update_settings(
        self,
        *,
        tenant_id: UUID,
        body: BusinessSettingsRequest,
    ) -> BusinessSettingsResponse:
        """The business's details, as the owner sends them."""
        tenant = self.tenant_repository.get_by_id(id=tenant_id)

        self.tenant_repository.update(
            tenant=tenant,
            values=body.model_dump(),
        )
        self._log("business_settings_updated", tenant_id)

        return BusinessSettingsResponse.model_validate(tenant)

    def list_locations(
        self,
        *,
        tenant_id: UUID,
    ) -> list[BusinessLocationResponse]:
        return [
            _to_location(location, services_offered)
            for location, services_offered in self.location_repository.list_for_tenant_with_services_offered(
                tenant_id=tenant_id,
            )
        ]

    @transactional
    def create_location(
        self,
        *,
        tenant_id: UUID,
        body: BusinessLocationRequest,
    ) -> BusinessLocationResponse:
        """
        A new location. The database gives it every service (not offered
        until its superadmin sets them up, trg_locations_create_services)
        and makes the owner its superadmin (trg_locations_grant_owner_superadmin).
        """
        location = self.location_repository.create(
            tenant_id=tenant_id,
            **body.model_dump(),
        )
        self._log("location_created", tenant_id, location.id)

        return _to_location(location, 0)

    @transactional
    def update_location(
        self,
        *,
        tenant_id: UUID,
        location_id: UUID,
        body: BusinessLocationRequest,
    ) -> BusinessLocationResponse:
        """
        A location's details. A new code is a new address: old links then
        lead to the landing page (the owner's choice; the form warns).
        """
        location = self.location_repository.get_by_id(id=location_id)

        if not location or location.tenant_id != tenant_id:
            raise LocationNotFoundError()

        self.location_repository.update(
            location=location,
            values=body.model_dump(),
        )
        self._log("location_updated", tenant_id, location_id)

        # The public page caches a location for a few minutes; show the
        # change straight away (this process's cache).
        cache_stores.location_branding.pop(location_id, None)

        [services_offered] = [
            offered
            for row, offered in self.location_repository.list_for_tenant_with_services_offered(
                tenant_id=tenant_id,
            )
            if row.id == location_id
        ]

        return _to_location(location, services_offered)

    def _log(self, event: str, tenant_id: UUID, location_id: UUID | None = None) -> None:
        logger.info(
            "Business settings changed",
            extra={
                "event": event,
                "result": "success",
                "reason": f"tenant_id={tenant_id}" + (f"; location_id={location_id}" if location_id else ""),
            },
        )
