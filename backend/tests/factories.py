import itertools
import json
import os
import uuid
from dataclasses import dataclass, field
from datetime import date, timedelta

import stripe
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import hash_password, hash_token
from app.errors.payments import PaymentProviderError
from app.integrations.payments.stripe.client import StripeAccount, StripeCheckout, StripeRefund
from app.integrations.storage.base import SignedUpload, StoredObject
from app.main import app


# Every customer gets their own phone (new_phone): a phone number belongs to
# one family across the tenant, and their pickup row follows it.
# Everything booking needs except the two phones (made per customer).
COMPLETE_PROFILE = {
    "address_line_1": "1 Test Street",
    "suburb": "Brisbane",
    "state": "QLD",
    "postcode": "4000",
    "emergency_contact_name": "Robin Contact",
    "emergency_contact_relation": "grandparent",
}

PASSWORD = "Password123"


def new_email(name: str = "pickup") -> str:
    return f"{name}-{uuid.uuid4().hex[:12]}@test.com"


@dataclass
class FakeEmailState:
    """Emails the app would have sent, for tests to inspect."""

    # Messages sent after their transaction committed (EmailOutbox).
    messages: list = field(default_factory=list)


class FakeEmail:
    """Stands in for EmailClient (patched in conftest), so no test sends."""

    state = FakeEmailState()

    def send(self, message):
        self.state.messages.append(message)


@dataclass
class FakeStorageState:
    """What's in the fake bucket, and what the app asked of it."""

    # (bucket, key) -> {"content", "content_type", "metadata"}
    objects: dict[tuple[str, str], dict] = field(default_factory=dict)
    # Policies handed out for browser uploads, by key.
    uploads: dict[str, dict] = field(default_factory=dict)
    download_links: list[dict] = field(default_factory=list)


class FakeStorage:
    """
    Stands in for StorageClient in every service (patched in conftest), so
    no test talks to GCS or S3. `receive` plays the browser's upload,
    enforcing the signed policy the way the provider would.
    """

    state = FakeStorageState()
    provider = "gcs"
    bucket = "test-documents"

    def create_upload(self, *, key, content_type, max_size_bytes, metadata, expires_in):
        self.state.uploads[key] = {
            "content_type": content_type,
            "max_size_bytes": max_size_bytes,
            "metadata": metadata,
        }

        return SignedUpload(
            url=f"https://storage.test/{self.bucket}",
            fields={"key": key, "Content-Type": content_type},
        )

    def get_object(self, *, bucket, key):
        stored = self.state.objects.get((bucket, key))

        if stored is None:
            return None

        return StoredObject(size_bytes=len(stored["content"]), content_type=stored["content_type"])

    def read_start(self, *, bucket, key, length):
        return self.state.objects[(bucket, key)]["content"][:length]

    def copy(self, *, bucket, source_key, target_key):
        self.state.objects[(bucket, target_key)] = dict(self.state.objects[(bucket, source_key)])

    def delete(self, *, bucket, key):
        self.state.objects.pop((bucket, key), None)

    def create_download_url(self, *, bucket, key, content_type, filename, expires_in):
        self.state.download_links.append({"bucket": bucket, "key": key, "content_type": content_type})

        return f"https://storage.test/{bucket}/{key}?signed"

    @classmethod
    def receive(cls, upload: dict, content: bytes) -> bool:
        """
        The browser posting a file with the signed fields from an upload
        response. Like the provider, refuses a file over the policy's size
        and stores the policy's content type whatever the file is.
        """
        key = upload["fields"]["key"]
        policy = cls.state.uploads[key]

        if not 1 <= len(content) <= policy["max_size_bytes"]:
            return False

        cls.state.objects[(cls.bucket, key)] = {
            "content": content,
            "content_type": policy["content_type"],
            "metadata": policy["metadata"],
        }

        return True

    @classmethod
    def keys(cls) -> set[str]:
        return {key for (_, key) in cls.state.objects}


def new_phone() -> str:
    """A unique-enough Australian mobile number."""
    return "04" + str(uuid.uuid4().int)[:8]


@dataclass
class Customer:
    client: TestClient
    email: str
    password: str
    phone: str | None = None


@dataclass
class StaffMember:
    """A staff-role user: their website login and their staff kiosk PIN."""

    client: TestClient
    email: str
    user_id: str
    pin: str | None


@dataclass
class FakeStripeState:
    """What the fake Stripe has been asked to do, for tests to inspect."""

    sessions: dict[str, StripeCheckout] = field(default_factory=dict)
    metadata: dict[str, dict] = field(default_factory=dict)
    created: list[dict] = field(default_factory=list)

    # Refunds by Stripe refund id: what was asked for, with its metadata
    # and the connected account it was made in.
    refunds: dict[str, dict] = field(default_factory=dict)

    # The connected account each checkout session was made in (None: the
    # platform's), so webhooks come from the right account.
    session_accounts: dict[str, str | None] = field(default_factory=dict)

    # Connected accounts the fake has created, by id, and onboarding links.
    accounts: dict[str, StripeAccount] = field(default_factory=dict)
    onboarding_links: list[dict] = field(default_factory=list)

    # "Connect with Stripe": the links handed out, and the account each
    # OAuth code links (tests set these).
    oauth_links: list[dict] = field(default_factory=list)
    oauth_codes: dict[str, str] = field(default_factory=dict)


class FakeStripe:
    """
    Stands in for StripeClient in every service (patched in conftest), so
    no test talks to Stripe. Webhook payloads are plain JSON and the
    signature "invalid" is rejected, mimicking a forged request. Like the
    real client, it's made for one connected account (or the platform).
    """

    state = FakeStripeState()

    def __init__(self, *, account_id: str | None = None):
        self.account_id = account_id

    def create_checkout_session(self, *, line_items, currency, metadata, success_url, cancel_url, idempotency_key):
        session_id = f"cs_test_{uuid.uuid4().hex}"

        checkout = StripeCheckout(
            checkout_url=f"https://checkout.stripe.test/{session_id}",
            checkout_session_id=session_id,
            payment_intent_id=None,
            status="open",
        )

        self.state.sessions[session_id] = checkout
        self.state.metadata[session_id] = metadata
        self.state.session_accounts[session_id] = self.account_id
        self.state.created.append(
            {
                "session_id": session_id,
                "account_id": self.account_id,
                "line_items": line_items,
                "currency": currency,
                "success_url": success_url,
                "cancel_url": cancel_url,
                "idempotency_key": idempotency_key,
            }
        )

        return checkout

    def get_checkout_session(self, *, checkout_session_id):
        return self.state.sessions[checkout_session_id]

    def expire_checkout_session(self, *, checkout_session_id):
        checkout = self.state.sessions[checkout_session_id]
        checkout.status = "expired"

        return checkout

    def get_receipt_url(self, *, payment_intent_id):
        return f"https://pay.stripe.test/receipts/{payment_intent_id}"

    def create_refund(self, *, payment_intent_id, amount_cents, metadata, idempotency_key):
        # Like Stripe, the same idempotency key returns the same refund.
        for refund_id, refund in self.state.refunds.items():
            if refund["idempotency_key"] == idempotency_key:
                return StripeRefund(refund_id=refund_id, status="pending")

        refund_id = f"re_test_{uuid.uuid4().hex}"

        self.state.refunds[refund_id] = {
            "account_id": self.account_id,
            "payment_intent_id": payment_intent_id,
            "amount_cents": amount_cents,
            "metadata": metadata,
            "idempotency_key": idempotency_key,
        }

        return StripeRefund(refund_id=refund_id, status="pending")

    def create_account(self, *, email, business_name):
        account = StripeAccount(
            account_id=f"acct_test_{uuid.uuid4().hex[:16]}",
            charges_enabled=False,
            payouts_enabled=False,
            details_submitted=False,
        )
        self.state.accounts[account.account_id] = account

        return account

    def get_account(self, *, account_id):
        return self.state.accounts[account_id]

    def create_onboarding_link(self, *, account_id, refresh_url, return_url):
        self.state.onboarding_links.append(
            {"account_id": account_id, "refresh_url": refresh_url, "return_url": return_url}
        )

        return f"https://connect.stripe.test/setup/{account_id}"

    def oauth_authorize_url(self, *, state, redirect_uri):
        self.state.oauth_links.append({"state": state, "redirect_uri": redirect_uri})

        return f"https://connect.stripe.test/oauth/authorize?state={state}"

    def complete_oauth(self, *, code):
        if code not in self.state.oauth_codes:
            raise PaymentProviderError(log_reason=f"Unknown OAuth code {code}")

        return self.state.oauth_codes[code]

    def construct_webhook_event(self, *, payload, signature, connect=False):
        if signature == "invalid":
            raise stripe.SignatureVerificationError("Invalid signature", signature)

        return json.loads(payload)



class Api:
    """Builds API clients and test data against the test database."""

    def __init__(self):
        self._client_ids = itertools.count(1)
        self._day_offsets = itertools.count(0)
        self.admin_db = create_engine(os.environ["DATABASE_ADMIN_URL"])

    # ---------------------------------------------------------------------
    # Clients
    # ---------------------------------------------------------------------

    def client(self, *, tenant: str = "tenant1") -> TestClient:
        """
        A new client with its own cookie jar and rate-limit bucket.

        On the tenant's own site, under /api, as the browser sees it: the
        host decides the tenant. HTTPS because the auth cookie is Secure;
        Origin because changes must come from the same site; a unique
        X-Forwarded-For so the rate limiter (keyed by client IP) treats each
        client separately.
        """
        n = next(self._client_ids)

        return TestClient(
            app,
            base_url=f"https://{tenant}.{settings.BASE_DOMAIN}/api",
            headers={
                "Origin": f"https://{tenant}.{settings.BASE_DOMAIN}",
                "X-Forwarded-For": f"10.{n // 65536 % 256}.{n // 256 % 256}.{n % 256}",
            },
        )

    def login(
        self,
        email: str,
        password: str,
        *,
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> TestClient:
        client = self.client(tenant=tenant)

        response = client.post(
            f"/auth/v1/login/{location}",
            json={"email": email, "password": password},
        )
        assert response.status_code == 200, response.text

        return client

    # ---------------------------------------------------------------------
    # Data through the API
    # ---------------------------------------------------------------------

    def new_customer(
        self,
        *,
        complete_profile: bool = True,
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> Customer:
        email = f"customer-{uuid.uuid4().hex[:12]}@test.com"

        response = self.client(tenant=tenant).post(
            f"/customer/v1/onboard/{location}",
            json={
                "email": email,
                "password": PASSWORD,
                "first_name": "Test",
                "last_name": "Customer",
                "terms_accepted": True,
            },
        )
        assert response.status_code == 201, response.text

        client = self.login(email, PASSWORD, tenant=tenant, location=location)

        phone = None

        if complete_profile:
            phone = new_phone()
            # The emergency contact's phone must differ from the parent's.
            emergency_phone = next(p for p in iter(new_phone, None) if p != phone)
            response = client.patch(
                "/customer/v1/profile",
                json={**COMPLETE_PROFILE, "phone": phone, "emergency_contact_phone": emergency_phone},
            )
            assert response.status_code == 200, response.text

        return Customer(client=client, email=email, password=PASSWORD, phone=phone)

    def new_staff(
        self,
        *,
        pin: str | None = "2580",
        role: str = "staff",
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> StaffMember:
        """
        A staff member (the staff role, or `role`) at the location, logged in on the
        website, with a staff kiosk PIN set there (unless pin is None).
        Staff accounts have no sign-up, so the user is inserted directly.
        """
        email = f"staff-{uuid.uuid4().hex[:12]}@test.com"

        [(user_id,)] = self.sql(
            """
            WITH new_user AS (
                INSERT INTO auth.users (email, password_hash, first_name, last_name, terms_accepted_at, is_active)
                VALUES (:email, :password_hash, 'Staff', 'Member', now(), TRUE)
                RETURNING id
            )
            INSERT INTO auth.location_user_roles (user_id, location_id, role_id)
            SELECT new_user.id, l.id, r.id
            FROM new_user, tenancy.locations l, tenancy.tenants t, auth.roles r
            WHERE l.tenant_id = t.id AND t.code = :tenant AND l.code = :location AND r.code = :role
            RETURNING user_id::text
            """,
            email=email,
            password_hash=hash_password(password=PASSWORD),
            tenant=tenant,
            location=location,
            role=role,
        )

        client = self.login(email, PASSWORD, tenant=tenant, location=location)

        if pin:
            response = client.put("/staff-pin/v1/", json={"password": PASSWORD, "pin": pin})
            assert response.status_code == 200, response.text

        return StaffMember(client=client, email=email, user_id=user_id, pin=pin)

    def new_child(self, customer: Customer, **overrides) -> dict:
        # Ten years old: inside the dev seed's 8-17 age range now and on the
        # factory's service days (~13 months out).
        body = {
            "first_name": "Child",
            "last_name": uuid.uuid4().hex[:8],
            "dob": date(date.today().year - 10, 3, 1).isoformat(),
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
            **overrides,
        }

        response = customer.client.post("/children/v1/", json=body)
        assert response.status_code == 201, response.text

        return response.json()["data"]

    def upload_document(
        self,
        customer: Customer,
        child_id: str,
        *,
        document_type: str = "asthma_action_plan",
    ) -> dict:
        """A PDF uploaded and accepted for the child, the way the frontend does it (sends them to review)."""
        content = b"%PDF-1.7\n" + b"0" * 200
        response = customer.client.post(
            "/child-documents/v1/",
            json={
                "child_id": child_id,
                "document_type": document_type,
                "filename": "plan.pdf",
                "content_type": "application/pdf",
                "size_bytes": len(content),
            },
        )
        assert response.status_code == 201, response.text

        started = response.json()["data"]
        assert FakeStorage.receive(started["upload"], content)

        response = customer.client.post(f"/child-documents/v1/{started['document']['id']}/complete")
        assert response.status_code == 200, response.text

        return response.json()["data"]

    def book(
        self,
        customer: Customer,
        selections: dict[str, list[str]],
        *,
        idempotency_key: str | None = None,
    ):
        """POST a booking; selections maps child_id -> service day ids."""
        return customer.client.post(
            "/booking/v1/",
            json={
                "idempotency_key": idempotency_key or uuid.uuid4().hex,
                "bookings": [
                    {"child_id": child_id, "location_service_days": day_ids}
                    for child_id, day_ids in selections.items()
                ],
            },
        )

    # ---------------------------------------------------------------------
    # Data the API can't create (inserted as the owner role)
    # ---------------------------------------------------------------------

    def service_day(
        self,
        *,
        service: str = "after_school_care",
        capacity: int = 30,
        is_open: bool = True,
        days_from_today: int | None = None,
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> str:
        """
        A service day. By default it's new and in the future: dates start
        ~13 months out (past the dev seed's calendar) and never repeat.
        `days_from_today` picks a specific date (e.g. 0 or -1), reusing the
        seeded day if there is one.
        """
        if days_from_today is None:
            days_from_today = 400 + next(self._day_offsets)

        service_date = date.today() + timedelta(days=days_from_today)

        with self.admin_db.begin() as conn:
            return str(
                conn.execute(
                    text("""
                        INSERT INTO public.location_service_days (
                            location_service_id, location_id, service_date, capacity, is_open
                        )
                        SELECT ls.id, ls.location_id, :service_date, :capacity, :is_open
                        FROM public.location_services ls
                        JOIN public.service_types st ON st.id = ls.service_type_id
                        JOIN tenancy.locations l ON l.id = ls.location_id
                        JOIN tenancy.tenants t ON t.id = l.tenant_id
                        WHERE st.code = :service
                          AND l.code = :location
                          AND t.code = :tenant
                        ON CONFLICT (location_service_id, service_date)
                        DO UPDATE SET
                            capacity = EXCLUDED.capacity,
                            is_open = EXCLUDED.is_open
                        RETURNING id;
                    """),
                    {
                        "service_date": service_date,
                        "capacity": capacity,
                        "is_open": is_open,
                        "service": service,
                        "location": location,
                        "tenant": tenant,
                    },
                ).scalar_one()
            )

    def booking_today(self, customer: Customer, child_id: str, **options) -> str:
        """A confirmed booking for today, at the location's own date. Returns its id."""
        return self.booking_on(customer, child_id, days_from_today=0, **options)

    def booking_on(
        self,
        customer: Customer,
        child_id: str,
        *,
        days_from_today: int,
        service: str = "after_school_care",
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> str:
        """
        A confirmed booking for today or an earlier day (days_from_today 0
        or negative), at the location's own date. Bookings can only be made
        for later days, so this books and pays for a new future day, then
        moves the booking (the booking rules only run on insert). Returns
        the booking id.
        """
        response = self.book(customer, {child_id: [self.service_day(service=service, tenant=tenant, location=location)]})
        assert response.status_code == 201, response.text

        data = response.json()["data"]
        self.webhook("checkout.session.completed", self.session_id(data["checkout_url"]))

        [(booking_id,)] = self.sql(
            """
            WITH today AS (
                INSERT INTO public.location_service_days (
                    location_service_id, location_id, service_date, capacity, is_open
                )
                SELECT d.location_service_id, d.location_id,
                       (now() AT TIME ZONE l.timezone)::date + :days, 100, TRUE
                FROM public.bookings b
                JOIN public.location_service_days d ON d.id = b.location_service_day_id
                JOIN tenancy.locations l ON l.id = b.location_id
                WHERE b.booking_group_id = :group_id
                ON CONFLICT (location_service_id, service_date) DO UPDATE SET is_open = TRUE
                RETURNING id
            )
            UPDATE public.bookings
            SET location_service_day_id = (SELECT id FROM today)
            WHERE booking_group_id = :group_id
            RETURNING id::text
            """,
            group_id=data["booking_group_id"],
            days=days_from_today,
        )

        return booking_id

    def kiosk(
        self,
        admin: TestClient,
        kind: str = "family",
        *,
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> TestClient:
        """
        A tablet paired as the location's kiosk of this kind, by its admin.
        A location has one active kiosk of each kind, so any earlier one
        (from another test) is revoked first.
        """
        self.sql(
            """
            UPDATE public.location_kiosk_devices d
            SET is_active = FALSE
            FROM tenancy.locations l
            JOIN tenancy.tenants t ON t.id = l.tenant_id
            WHERE d.location_id = l.id
              AND d.kind = CAST(:kind AS public.kiosk_kind_enum)
              AND l.code = :location
              AND t.code = :tenant
            """,
            kind=kind,
            location=location,
            tenant=tenant,
        )

        response = admin.post("/kiosk-devices/v1/", json={"kind": kind, "name": f"{kind} kiosk"})
        assert response.status_code == 201, response.text

        tablet = self.client(tenant=tenant)
        response = tablet.post(f"/kiosk/v1/{location}/pair", json={"code": response.json()["data"]["setup_code"]})
        assert response.status_code == 200, response.text

        return tablet

    # ---------------------------------------------------------------------
    # Stripe
    # ---------------------------------------------------------------------

    def webhook(
        self,
        event_type: str,
        checkout_session_id: str,
        *,
        payment_status: str = "paid",
        signature: str = "test",
    ):
        """
        Deliver a Stripe webhook for a session the fake created, from the
        account it was made in (the Connect endpoint for a tenant's account).
        """
        event = {
            "type": event_type,
            "data": {
                "object": {
                    "id": checkout_session_id,
                    "payment_status": payment_status,
                    "payment_intent": f"pi_test_{uuid.uuid4().hex[:12]}",
                    "metadata": FakeStripe.state.metadata.get(checkout_session_id, {}),
                }
            },
        }

        return self._deliver(event, FakeStripe.state.session_accounts.get(checkout_session_id), signature)

    def _deliver(self, event: dict, account_id: str | None, signature: str = "test"):
        """Post an event to the endpoint Stripe would use for its account."""
        if account_id:
            event = {**event, "account": account_id}

        return self.client().post(
            "/v1/webhooks/stripe/connect" if account_id else "/v1/webhooks/stripe",
            content=json.dumps(event),
            headers={"Stripe-Signature": signature},
        )

    def refund_webhook(
        self,
        event_type: str,
        stripe_refund_id: str,
        *,
        status: str,
        metadata: dict | None = None,
    ):
        """Deliver a Stripe refund webhook for a refund the fake created."""
        refund = FakeStripe.state.refunds.get(stripe_refund_id, {})

        event = {
            "type": event_type,
            "data": {
                "object": {
                    "id": stripe_refund_id,
                    "status": status,
                    "metadata": refund.get("metadata", {}) if metadata is None else metadata,
                }
            },
        }

        return self._deliver(event, refund.get("account_id"))

    @staticmethod
    def session_id(checkout_url: str) -> str:
        return checkout_url.rsplit("/", 1)[-1]

    def reset_token(self, email: str) -> str:
        """Issue a password reset token at the user's location, as the
        forgot-password email would carry."""
        raw_token = uuid.uuid4().hex

        with self.admin_db.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO auth.password_reset_tokens (
                        user_id, location_id, token_hash, expires_at
                    )
                    SELECT u.id, lur.location_id, :token_hash, now() + interval '30 minutes'
                    FROM auth.users u
                    JOIN auth.location_user_roles lur ON lur.user_id = u.id
                    WHERE u.email = :email
                    LIMIT 1;
                """),
                {"token_hash": hash_token(token=raw_token), "email": email},
            )

        return raw_token

    def sql(self, query: str, **params):
        """Run SQL as the owner role (RLS doesn't apply) and return rows."""
        with self.admin_db.begin() as conn:
            result = conn.execute(text(query), params)
            return result.all() if result.returns_rows else None
