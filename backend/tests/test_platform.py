"""
The platform's site (docs/tenant-administration.md, stage 4): its admins log
in on the bare base domain, invite businesses and switch them off and on,
and never see a tenant's data; a business registers with its invite.
"""

import uuid
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from app.core.config import settings
from app.db.session import SessionLocal
from app.main import app
from tests.factories import PASSWORD, Api


PLATFORM_HOST = settings.BASE_DOMAIN


def _platform_client(**headers: str) -> TestClient:
    """A client on the platform's site (the bare base domain)."""
    return TestClient(
        app,
        base_url=f"https://{PLATFORM_HOST}/api",
        headers={
            "Origin": f"https://{PLATFORM_HOST}",
            "X-Forwarded-For": f"10.250.{uuid.uuid4().int % 250}.{uuid.uuid4().int % 250}",
            **headers,
        },
    )


@pytest.fixture
def platform() -> TestClient:
    """The seeded platform admin, logged in on the platform's site."""
    client = _platform_client()
    response = client.post("/platform/v1/login", json={"email": "platform@test.com", "password": "123"})
    assert response.status_code == 200, response.text

    return client


def _invite(platform: TestClient, email: str | None = None) -> tuple[dict, str]:
    """A new invite and its one-time token."""
    email = email or f"owner-{uuid.uuid4().hex[:10]}@test.com"
    response = platform.post("/platform/v1/invites", json={"email": email})
    assert response.status_code == 201, response.text
    invite = response.json()["data"]

    [token] = parse_qs(urlparse(invite["url"]).query)["invite"]

    return invite, token


def _register(token: str, code: str | None = None):
    code = code or f"biz-{uuid.uuid4().hex[:8]}"

    return code, _platform_client().post(
        "/registration/v1/register",
        json={
            "invite": token,
            "business_name": "New Business",
            "code": code,
            "first_name": "New",
            "last_name": "Owner",
            "password": PASSWORD,
            "terms_accepted": True,
        },
    )


def _new_tenant(platform: TestClient) -> tuple[str, str]:
    """A business registered through an invite: (its code, its owner's email)."""
    invite, token = _invite(platform)
    code, response = _register(token)
    assert response.status_code == 201, response.text

    return code, invite["email"]


def _business_login(api: Api, tenant: str, email: str, password: str = PASSWORD):
    client = api.client(tenant=tenant)

    return client, client.post("/auth/v1/business/login", json={"email": email, "password": password})


# ---------------------------------------------------------------------------
# Logging in
# ---------------------------------------------------------------------------


# A platform admin logs in on the platform's site; a wrong password is
# refused, and a tenant's site has no platform login.
def test_platform_login(platform):
    assert platform.get("/platform/v1/session").json()["data"]["email"] == "platform@test.com"

    wrong = _platform_client().post("/platform/v1/login", json={"email": "platform@test.com", "password": "nope"})
    on_tenant_site = TestClient(
        app,
        base_url=f"https://tenant1.{settings.BASE_DOMAIN}/api",
        headers={"Origin": f"https://tenant1.{settings.BASE_DOMAIN}"},
    ).post("/platform/v1/login", json={"email": "platform@test.com", "password": "123"})

    assert wrong.status_code == 401
    assert on_tenant_site.status_code == 404


# A tenant's login is no platform login, and a platform login is no
# tenant's, even with the token moved across.
def test_tokens_dont_cross(api: Api, platform, owner):
    tenant_token = owner.cookies.get("access_token")
    platform_token = platform.cookies.get("platform_token")

    as_platform = _platform_client(Cookie=f"platform_token={tenant_token}").get("/platform/v1/tenants")
    as_tenant = api.client().get("/auth/v1/session", headers={"Cookie": f"access_token={platform_token}"})

    assert as_platform.status_code == 401
    assert as_tenant.status_code == 401
    assert _platform_client().get("/platform/v1/tenants").status_code == 401


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------


# The platform lists every business with its location count and whether it
# takes payments.
def test_list_tenants(platform):
    tenants = {t["code"]: t for t in platform.get("/platform/v1/tenants").json()["data"]}

    assert tenants["tenant1"]["location_count"] >= 2
    assert tenants["tenant1"]["takes_payments"] is True
    assert tenants["tenant1"]["is_active"] is True


# A platform admin sees no tenant data, even straight in the database.
def test_platform_admin_sees_no_tenant_data(api: Api):
    [(admin_id,)] = api.sql("SELECT id::text FROM auth.platform_admins WHERE email = 'platform@test.com'")

    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.platform_admin_id', :id, true)"), {"id": admin_id})

        for table in ("auth.users", "public.bookings", "public.child_profile", "public.customer_profile"):
            assert db.execute(text(f"SELECT count(*) FROM {table}")).scalar() == 0, table

        updated = db.execute(text("UPDATE tenancy.tenants SET name = 'Taken over'")).rowcount
        db.rollback()

    assert updated == 0


# Switching a business off makes its site answer as if it didn't exist (no
# pages, no logins); switching it on brings it back.
def test_switch_a_business_off_and_on(api: Api, platform):
    code, email = _new_tenant(platform)
    [(tenant_id,)] = api.sql("SELECT id::text FROM tenancy.tenants WHERE code = :c", c=code)

    assert platform.put(f"/platform/v1/tenants/{tenant_id}/active", json={"is_active": False}).status_code == 200
    assert api.client(tenant=code).get("/location-branding/v1/public").status_code == 404
    assert _business_login(api, code, email)[1].status_code == 404

    assert platform.put(f"/platform/v1/tenants/{tenant_id}/active", json={"is_active": True}).status_code == 200
    assert _business_login(api, code, email)[1].status_code == 200


# Only the platform can switch a business off, even straight in the database.
def test_only_the_platform_switches_businesses(api: Api):
    [(owner_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = 'sa1user@test.com'")

    with SessionLocal() as db:
        db.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": owner_id})

        with pytest.raises(DBAPIError, match="Only the platform"):
            db.execute(text("SELECT auth.set_tenant_active((SELECT id FROM tenancy.tenants WHERE code = 'tenant1'), FALSE)"))

        db.rollback()


# ---------------------------------------------------------------------------
# Invites and registration
# ---------------------------------------------------------------------------


# A business registers with its invite: the owner (the invite's email)
# logs in to its own Business settings with every tenant permission, and
# becomes superadmin at its first location. The invite is then used up.
def test_register_with_an_invite(api: Api, platform):
    invite, token = _invite(platform)

    details = _platform_client().get(f"/registration/v1/invites/{token}")
    assert details.json()["data"]["email"] == invite["email"]

    code, response = _register(token)
    assert response.status_code == 201, response.text
    assert response.json()["data"]["business_login_url"].endswith("/business/login")
    assert code in response.json()["data"]["business_login_url"]

    owner, login = _business_login(api, code, invite["email"])
    assert login.status_code == 200, login.text
    assert len(owner.get("/auth/v1/session").json()["data"]["tenant_permissions"]) == 5

    location = owner.post(
        "/business/v1/locations",
        json={
            "name": "First Centre", "code": "first", "address_line_1": "1 Test Street",
            "suburb": "Brisbane City", "state": "QLD", "postcode": "4000",
        },
    )
    assert location.status_code == 201, location.text
    assert owner.post("/auth/v1/switch-location/first").status_code == 200

    assert _register(token)[1].status_code == 400
    assert invite["id"] not in {i["id"] for i in platform.get("/platform/v1/invites").json()["data"]}


# A revoked or expired invite can't be used, nor looked up.
def test_revoked_and_expired_invites(api: Api, platform):
    revoked, revoked_token = _invite(platform)
    assert platform.delete(f"/platform/v1/invites/{revoked['id']}").status_code == 200

    expired, expired_token = _invite(platform)
    api.sql("UPDATE auth.tenant_invites SET expires_at = now() - interval '1 minute' WHERE id = CAST(:i AS uuid)", i=expired["id"])

    for token in (revoked_token, expired_token, "not-a-token"):
        assert _platform_client().get(f"/registration/v1/invites/{token}").status_code == 400
        assert _register(token)[1].status_code == 400


# A business's web address can't be another's, or one the platform uses.
def test_registration_checks_the_web_address(platform):
    _, taken_token = _invite(platform)
    _, reserved_token = _invite(platform)

    assert _register(taken_token, code="tenant1")[1].status_code == 409
    assert _register(reserved_token, code="www")[1].status_code == 400


# Registration is on the platform's site only.
def test_registration_is_on_the_platform_site(api: Api, platform):
    _, token = _invite(platform)

    assert api.client().get(f"/registration/v1/invites/{token}").status_code == 404
