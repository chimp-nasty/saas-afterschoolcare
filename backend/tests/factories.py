import itertools
import os
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import hash_token
from app.main import app


COMPLETE_PROFILE = {
    "phone": "0400000000",
    "address_line_1": "1 Test Street",
    "suburb": "Brisbane",
    "state": "QLD",
    "postcode": "4000",
}

PASSWORD = "Password123"


@dataclass
class Customer:
    client: TestClient
    email: str
    password: str


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

        HTTPS because the auth cookie is Secure; Origin because login and
        signup resolve the tenant from it; a unique X-Forwarded-For so the
        rate limiter (keyed by client IP) treats each client separately.
        """
        n = next(self._client_ids)

        return TestClient(
            app,
            base_url="https://testserver",
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

        if complete_profile:
            response = client.patch("/customer/v1/profile", json=COMPLETE_PROFILE)
            assert response.status_code == 200, response.text

        return Customer(client=client, email=email, password=PASSWORD)

    def new_child(self, customer: Customer, **overrides) -> dict:
        body = {
            "first_name": "Child",
            "last_name": uuid.uuid4().hex[:8],
            "dob": "2019-03-01",
            "medical_info": None,
            "allergy_info": None,
            "medication_info": None,
            **overrides,
        }

        response = customer.client.post("/children/v1/", json=body)
        assert response.status_code == 201, response.text

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
        tenant: str = "tenant1",
        location: str = "location1",
    ) -> str:
        """
        A new open service day. Dates start ~13 months out (past the dev
        seed's calendar) and never repeat, so days never collide.
        """
        service_date = date.today() + timedelta(days=400 + next(self._day_offsets))

        with self.admin_db.begin() as conn:
            return str(
                conn.execute(
                    text("""
                        INSERT INTO public.location_service_days (
                            location_service_id, location_id, service_date, capacity
                        )
                        SELECT ls.id, ls.location_id, :service_date, :capacity
                        FROM public.location_services ls
                        JOIN public.service_types st ON st.id = ls.service_type_id
                        JOIN tenancy.locations l ON l.id = ls.location_id
                        JOIN tenancy.tenants t ON t.id = l.tenant_id
                        WHERE st.code = :service
                          AND l.code = :location
                          AND t.code = :tenant
                        RETURNING id;
                    """),
                    {
                        "service_date": service_date,
                        "capacity": capacity,
                        "service": service,
                        "location": location,
                        "tenant": tenant,
                    },
                ).scalar_one()
            )

    def reset_token(self, email: str) -> str:
        """Issue a password reset token (email delivery isn't built yet)."""
        raw_token = uuid.uuid4().hex

        with self.admin_db.begin() as conn:
            conn.execute(
                text("""
                    INSERT INTO auth.password_reset_tokens (
                        user_id, token_hash, expires_at
                    )
                    SELECT id, :token_hash, now() + interval '30 minutes'
                    FROM auth.users
                    WHERE email = :email;
                """),
                {"token_hash": hash_token(token=raw_token), "email": email},
            )

        return raw_token

    def sql(self, query: str, **params):
        """Run SQL as the owner role (RLS doesn't apply) and return rows."""
        with self.admin_db.begin() as conn:
            result = conn.execute(text(query), params)
            return result.all() if result.returns_rows else None
