"""
Tenant permissions (docs/tenant-administration.md, stage 2): the tenant's
owner holds them directly, they travel in the token apart from the
location's, the database checks them live, and the owner is superadmin at
every location of the tenant.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.auth.jwt.context import TokenContext
from app.auth.jwt.tokens import TokenService
from app.db.session import SessionLocal
from app.dependencies.auth import require_permission, require_tenant_permission
from app.errors.auth import PermissionNotFoundError
from tests.factories import Api


TENANT_PERMISSIONS = {
    "tenant_settings": ["r", "u"],
    "tenant_locations": ["c", "r", "u"],
    "tenant_stripe_account": ["r", "u"],
    "tenant_domains": ["r", "u"],
}

NEW_LOCATION = """
    INSERT INTO tenancy.locations (tenant_id, code, name, address_line_1, suburb, state, postcode)
    SELECT t.id, :code, 'New location', '1 Test Street', 'Brisbane', 'QLD', '4000'
    FROM tenancy.tenants t
    WHERE t.code = 'tenant1'
    RETURNING id
"""


def _claims(client) -> dict:
    return TokenService.decode_access_token(client.cookies.get("access_token"))


def _user_id(api: Api, email: str) -> str:
    [(user_id,)] = api.sql("SELECT id::text FROM auth.users WHERE email = :e", e=email)
    return user_id


def _as(user_id: str):
    """An app database session (RLS applies) acting as the user."""
    db = SessionLocal()
    db.execute(text("SELECT set_config('app.user_id', :u, true)"), {"u": user_id})
    return db


# The owner's token carries every tenant permission; an admin's and a
# family's carry none.
def test_only_the_owner_has_tenant_permissions(api: Api, owner, admin, customer):
    assert _claims(owner)["tenant_permissions"] == TENANT_PERMISSIONS
    assert _claims(admin)["tenant_permissions"] == {}
    assert _claims(customer.client)["tenant_permissions"] == {}


# The owner is superadmin at every location of the tenant, so they can log
# in at either of tenant1's.
def test_owner_is_superadmin_at_every_location(api: Api):
    for location in ("location1", "location2"):
        client = api.login("sa1user@test.com", "123", tenant="tenant1", location=location)

        assert "superadmin" in _claims(client)["roles"]


# Adding a location makes the owner its superadmin straight away.
def test_new_location_makes_the_owner_superadmin(api: Api):
    owner_id = _user_id(api, "sa1user@test.com")

    with _as(owner_id) as db:
        location_id = db.execute(text(NEW_LOCATION), {"code": f"new-{uuid.uuid4().hex[:8]}"}).scalar_one()

        roles = db.execute(
            text("""
                SELECT r.code
                FROM auth.location_user_roles lur
                JOIN auth.roles r ON r.id = lur.role_id
                WHERE lur.location_id = :l AND lur.user_id = :u
            """),
            {"l": location_id, "u": owner_id},
        ).scalars().all()

        db.rollback()

    assert roles == ["superadmin"]


# Only the owner can add a location: an admin (or another superadmin) is
# refused by the database.
def test_only_the_owner_adds_locations(api: Api):
    other_superadmin = api.new_staff(role="superadmin", pin=None)

    for user_id in (_user_id(api, "t1user@test.com"), other_superadmin.user_id):
        with _as(user_id) as db:
            with pytest.raises(DBAPIError, match="row-level security"):
                db.execute(text(NEW_LOCATION), {"code": f"new-{uuid.uuid4().hex[:8]}"})

            db.rollback()


# Another tenant's owner can't change this tenant's Stripe account, even
# straight in the database; this tenant's owner can.
def test_owners_only_change_their_own_tenant(api: Api):
    update = text("""
        UPDATE tenancy.tenant_stripe_accounts
        SET disconnected_at = now()
        WHERE tenant_id = (SELECT id FROM tenancy.tenants WHERE code = 'tenant1')
    """)

    with _as(_user_id(api, "sa2user@test.com")) as db:
        assert db.execute(update).rowcount == 0
        db.rollback()

    with _as(_user_id(api, "sa1user@test.com")) as db:
        assert db.execute(update).rowcount == 1
        db.rollback()


# A role can't be given a tenant permission, and nobody but the owner can
# hold one.
def test_tenant_permissions_stay_with_the_owner(api: Api):
    with pytest.raises(IntegrityError):
        api.sql("""
            INSERT INTO auth.role_permissions (role_id, permission_id, channel)
            SELECT r.id, p.id, 'web'
            FROM auth.roles r, auth.permissions p
            WHERE r.code = 'superadmin' AND p.resource = 'tenant_settings' AND p.action = 'u'
        """)

    with pytest.raises(IntegrityError):
        api.sql("""
            INSERT INTO auth.user_tenant_permissions (user_id, tenant_id, permission_id)
            SELECT u.id, t.id, p.id
            FROM auth.users u, tenancy.tenants t, auth.permissions p
            WHERE u.email = 't1user@test.com' AND t.code = 'tenant1'
              AND p.resource = 'tenant_settings' AND p.action = 'u'
        """)


# A tenant permission never satisfies a location check, nor the other way
# round, even with the same name.
def test_tenant_and_location_permissions_are_separate():
    ctx = TokenContext(
        user_id=uuid.uuid4(),
        tenant_id=uuid.uuid4(),
        location_id=uuid.uuid4(),
        email=None,
        first_name=None,
        roles=(),
        permissions={"stripe_account": frozenset({"r", "u"})},
        tenant_permissions={"tenant_stripe_account": frozenset({"u"}), "stripe_account": frozenset({"u"})},
    )

    with pytest.raises(PermissionNotFoundError):
        require_tenant_permission(resource="stripe_account", action="r")(ctx=ctx)

    with pytest.raises(PermissionNotFoundError):
        require_permission(resource="tenant_stripe_account", action="u")(ctx=ctx)

    assert require_tenant_permission(resource="tenant_stripe_account", action="u")(ctx=ctx) is ctx


# Location codes can't take the names of the site's own pages.
@pytest.mark.parametrize("code", ["business", "api", "kiosk", "locations", "about"])
def test_reserved_location_codes(api: Api, code):
    with pytest.raises(IntegrityError, match="ck_locations_code_reserved"):
        api.sql(NEW_LOCATION.replace("RETURNING id", ""), code=code)
