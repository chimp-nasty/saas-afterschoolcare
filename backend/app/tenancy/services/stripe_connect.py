import logging
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth.repositories.rls_context import RlsContextRepository
from app.core.config import settings
from app.db.transaction import transactional
from app.errors.base import ApplicationError
from app.errors.payments import (
    PaymentProviderError,
    StripeAccountLinkedError,
    StripeAccountNotFoundError,
    StripeOAuthUnavailableError,
)
from app.integrations.payments.stripe.client import StripeClient
from app.tenancy.repositories.location import LocationRepository
from app.tenancy.repositories.stripe_account import TenantStripeAccountRepository
from app.tenancy.repositories.tenant import TenantRepository
from app.tenancy.schemas.stripe_account import StripeAccountStatusResponse, StripeOnboardingResponse
from app.tenancy.site_url import location_site_url
from app.tenancy.stripe_oauth_state import OAuthState, decode_state, encode_state

# Where Stripe's OAuth returns (registered in Stripe's OAuth settings).
OAUTH_CALLBACK_PATH = "/stripe-account/v1/oauth/callback"


logger = logging.getLogger("app.payments")


class StripeConnectService:
    """
    Admin › Payments (slice 5): the business's own Stripe account (Stripe
    Connect, a Standard account with direct charges). Admins see whether
    it can take payments (stripe_account r); superadmins connect it, either
    linking the account they already have ("Connect with Stripe", OAuth)
    or making a new one through Stripe's hosted onboarding, refresh its
    status, and turn payments off and on in our app (stripe_account u).
    Whether bookings and checkouts may happen is the database's
    (tenancy.payments_account).
    """

    def __init__(
        self,
        *,
        db: Session,
        stripe_account_repository: TenantStripeAccountRepository,
        location_repository: LocationRepository,
        tenant_repository: TenantRepository,
        rls_context: RlsContextRepository,
    ):
        self.db = db
        self.rls_context = rls_context
        self.stripe_account_repository = stripe_account_repository
        self.location_repository = location_repository
        self.tenant_repository = tenant_repository

    def status(
        self,
        *,
        location_id: UUID,
    ) -> StripeAccountStatusResponse:
        location = self.location_repository.get_by_id(id=location_id)
        account = self.stripe_account_repository.get_for_tenant(tenant_id=location.tenant_id)
        takes_payments = self.db.execute(
            select(func.tenancy.payments_account(location_id))
        ).scalar() is not None

        return StripeAccountStatusResponse(
            connected=account is not None,
            stripe_account_id=account.stripe_account_id if account else None,
            is_linked=bool(account and account.is_linked),
            details_submitted=bool(account and account.details_submitted),
            charges_enabled=bool(account and account.charges_enabled),
            payouts_enabled=bool(account and account.payouts_enabled),
            disconnected=bool(account and account.disconnected_at),
            revoked=bool(account and account.revoked_at),
            takes_payments=takes_payments,
            connected_at=account.connected_at if account else None,
            can_link_existing=bool(settings.STRIPE_CONNECT_CLIENT_ID),
        )

    def oauth_link(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        origin: str | None,
    ) -> StripeOnboardingResponse:
        """
        "Connect with Stripe": Stripe's page to log in and link the
        business's existing account. Stripe returns to the API's callback
        (one registered address for every tenant), which sends them back to
        this location's site.
        """
        if not settings.STRIPE_CONNECT_CLIENT_ID:
            raise StripeOAuthUnavailableError()

        location = self.location_repository.get_by_id(id=location_id)
        tenant = self.tenant_repository.get_by_id(id=location.tenant_id)
        site_url = location_site_url(location=location, tenant=tenant, origin=origin)

        url = StripeClient().oauth_authorize_url(
            state=encode_state(OAuthState(user_id=user_id, location_id=location_id, site_url=site_url)),
            redirect_uri=f"{settings.API_BASE_URL.rstrip('/')}{OAUTH_CALLBACK_PATH}",
        )

        return StripeOnboardingResponse(url=url)

    def complete_oauth(
        self,
        *,
        code: str | None,
        state: str | None,
        error: str | None,
    ) -> str | None:
        """
        Stripe's return from "Connect with Stripe": link the account and say
        where to send the browser (Admin › Payments, with how it went), or
        None when the state isn't ours (nowhere safe to send them). The
        account is saved as the person who started it, so RLS lets only a
        superadmin of that business link it.
        """
        started = decode_state(state) if state else None

        if not started:
            return None

        back = f"{started.site_url}/admin/payments?stripe="

        if error or not code:
            return f"{back}cancelled"

        try:
            account_id = StripeClient().complete_oauth(code=code)
            self._link_account(started=started, account_id=account_id)
        except (ApplicationError, PaymentProviderError) as exc:
            logger.warning(
                "Couldn't link a Stripe account",
                extra={"event": "stripe_oauth_failed", "result": "failed", "reason": getattr(exc, "log_reason", None) or exc.message},
            )

            return f"{back}{'taken' if exc.status_code == 409 else 'error'}"

        return f"{back}connected"

    @transactional
    def _link_account(self, *, started: OAuthState, account_id: str) -> None:
        self.rls_context.set_user_id(user_id=started.user_id)
        self.rls_context.set_location_id(location_id=started.location_id)

        location = self.location_repository.get_by_id(id=started.location_id)
        stripe_account = StripeClient().get_account(account_id=account_id)

        self.stripe_account_repository.connect(
            tenant_id=location.tenant_id,
            stripe_account_id=account_id,
            charges_enabled=stripe_account.charges_enabled,
            payouts_enabled=stripe_account.payouts_enabled,
            details_submitted=stripe_account.details_submitted,
            is_linked=True,
        )
        self._log("stripe_account_linked", location.tenant_id, account_id)

    def onboarding_link(
        self,
        *,
        location_id: UUID,
        origin: str | None,
    ) -> StripeOnboardingResponse:
        """
        Stripe's hosted onboarding for the business: a new Standard account
        the first time (or after the old one revoked our access), then the
        same account until onboarding is finished. Stripe sends them back
        to Admin › Payments.
        """
        location = self.location_repository.get_by_id(id=location_id)
        tenant = self.tenant_repository.get_by_id(id=location.tenant_id)
        site_url = location_site_url(location=location, tenant=tenant, origin=origin)
        account = self.stripe_account_repository.get_for_tenant(tenant_id=tenant.id)

        # A business's own linked account isn't ours to onboard: it finishes
        # setup in its Stripe dashboard (Stripe refuses our link for it).
        if account and account.is_linked and not account.revoked_at:
            raise StripeAccountLinkedError()

        # Plain values only past this point: creating the account commits,
        # and the next transaction has no RLS settings to read rows with.
        if not account or account.revoked_at:
            account_id = self._create_account(tenant_id=tenant.id, email=tenant.email, name=tenant.name)
        else:
            account_id = account.stripe_account_id

        url = StripeClient().create_onboarding_link(
            account_id=account_id,
            refresh_url=f"{site_url}/admin/payments?stripe=refresh",
            return_url=f"{site_url}/admin/payments?stripe=return",
        )

        return StripeOnboardingResponse(url=url)

    @transactional
    def _create_account(self, *, tenant_id: UUID, email: str | None, name: str) -> str:
        """A new Stripe account for the tenant, saved; returns its id."""
        stripe_account = StripeClient().create_account(email=email, business_name=name)
        self.stripe_account_repository.connect(
            tenant_id=tenant_id,
            stripe_account_id=stripe_account.account_id,
            charges_enabled=stripe_account.charges_enabled,
            payouts_enabled=stripe_account.payouts_enabled,
            details_submitted=stripe_account.details_submitted,
        )
        self._log("stripe_account_created", tenant_id, stripe_account.account_id)

        return stripe_account.account_id

    @transactional
    def refresh(
        self,
        *,
        location_id: UUID,
    ) -> StripeAccountStatusResponse:
        """Ask Stripe for the account's flags now (the webhook does this too)."""
        account = self._account(location_id)
        stripe_account = StripeClient().get_account(account_id=account.stripe_account_id)

        self.stripe_account_repository.set_flags(
            account=account,
            charges_enabled=stripe_account.charges_enabled,
            payouts_enabled=stripe_account.payouts_enabled,
            details_submitted=stripe_account.details_submitted,
        )

        return self.status(location_id=location_id)

    @transactional
    def set_disconnected(
        self,
        *,
        location_id: UUID,
        disconnected: bool,
    ) -> StripeAccountStatusResponse:
        """
        Turn payments off in our app (or back on). New bookings stop while
        off; the account stays linked, so past payments can still be refunded.
        """
        account = self._account(location_id)

        self.stripe_account_repository.set_disconnected(account=account, disconnected=disconnected)
        self._log(
            "stripe_account_disconnected" if disconnected else "stripe_account_reconnected",
            account.tenant_id,
            account.stripe_account_id,
        )

        return self.status(location_id=location_id)

    def _account(self, location_id: UUID):
        location = self.location_repository.get_by_id(id=location_id)
        account = self.stripe_account_repository.get_for_tenant(tenant_id=location.tenant_id)

        if not account:
            raise StripeAccountNotFoundError()

        return account

    def _log(self, event: str, tenant_id: UUID, account_id: str) -> None:
        logger.info(
            "Stripe account changed",
            extra={"event": event, "result": "success", "reason": f"tenant_id={tenant_id}; account={account_id}"},
        )
