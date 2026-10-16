from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.security import hash_password


# =========================
# DEV USER CREDENTIALS
# =========================

DEV_PASSWORD = "123"

TENANT_1_USER_EMAIL = "t1user@test.com"
TENANT_1_USER_PASSWORD = DEV_PASSWORD

TENANT_2_USER_EMAIL = "t2user@test.com"
TENANT_2_USER_PASSWORD = DEV_PASSWORD


def up(conn: Connection) -> None:
    password_hash = hash_password(
        password=DEV_PASSWORD,
    )

    # =========================
    # TENANT 1
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.tenants (
                name,
                code,
                email,
                terms_accepted_at,
                terms_version,
                is_active
            )
            VALUES (
                'Tenant 1',
                'tenant1',
                'tenant_1@test.com',
                now(),
                'v1',
                TRUE
            )
            ON CONFLICT (code)
            DO NOTHING;
        """)
    )

    tenant_1_id = conn.execute(
        text("""
            SELECT id
            FROM tenancy.tenants
            WHERE code = 'tenant1';
        """)
    ).scalar_one()

    # =========================
    # TENANT 1 - LOCATION 1
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.locations (
                tenant_id,
                name,
                code,
                email,
                is_active
            )
            VALUES (
                :tenant_id,
                'Location 1',
                'location1',
                'tenant_1_location_1@test.com',
                TRUE
            )
            ON CONFLICT (
                tenant_id,
                code
            )
            DO NOTHING;
        """),
        {
            "tenant_id": tenant_1_id,
        },
    )

    tenant_1_location_1_id = conn.execute(
        text("""
            SELECT id
            FROM tenancy.locations
            WHERE
                tenant_id = :tenant_id
                AND code = 'location1';
        """),
        {
            "tenant_id": tenant_1_id,
        },
    ).scalar_one()

    # =========================
    # TENANT 1 - LOCATION 2
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.locations (
                tenant_id,
                name,
                code,
                email,
                is_active
            )
            VALUES (
                :tenant_id,
                'Location 2',
                'location2',
                'tenant_1_location_2@test.com',
                TRUE
            )
            ON CONFLICT (
                tenant_id,
                code
            )
            DO NOTHING;
        """),
        {
            "tenant_id": tenant_1_id,
        },
    )

    tenant_1_location_2_id = conn.execute(
        text("""
            SELECT id
            FROM tenancy.locations
            WHERE
                tenant_id = :tenant_id
                AND code = 'location2';
        """),
        {
            "tenant_id": tenant_1_id,
        },
    ).scalar_one()

    # =========================
    # TENANT 1 - USER
    # =========================

    conn.execute(
        text("""
            INSERT INTO auth.users (
                email,
                password_hash,
                first_name,
                last_name,
                terms_accepted_at,
                terms_version,
                is_active
            )
            VALUES (
                :email,
                :password_hash,
                'Tenant 1',
                'User',
                now(),
                'v1',
                TRUE
            )
            ON CONFLICT (email)
            DO NOTHING;
        """),
        {
            "email": TENANT_1_USER_EMAIL,
            "password_hash": password_hash,
        },
    )

    user_1_id = conn.execute(
        text("""
            SELECT id
            FROM auth.users
            WHERE email = :email;
        """),
        {
            "email": TENANT_1_USER_EMAIL,
        },
    ).scalar_one()

    # =========================
    # TENANT 2
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.tenants (
                name,
                code,
                email,
                terms_accepted_at,
                terms_version,
                is_active
            )
            VALUES (
                'Tenant 2',
                'tenant2',
                'tenant_2@test.com',
                now(),
                'v1',
                TRUE
            )
            ON CONFLICT (code)
            DO NOTHING;
        """)
    )

    tenant_2_id = conn.execute(
        text("""
            SELECT id
            FROM tenancy.tenants
            WHERE code = 'tenant2';
        """)
    ).scalar_one()

    # =========================
    # TENANT 2 - LOCATION 2
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.locations (
                tenant_id,
                name,
                code,
                email,
                is_active
            )
            VALUES (
                :tenant_id,
                'Location 2',
                'location2',
                'tenant_2_location_2@test.com',
                TRUE
            )
            ON CONFLICT (
                tenant_id,
                code
            )
            DO NOTHING;
        """),
        {
            "tenant_id": tenant_2_id,
        },
    )

    tenant_2_location_2_id = conn.execute(
        text("""
            SELECT id
            FROM tenancy.locations
            WHERE
                tenant_id = :tenant_id
                AND code = 'location2';
        """),
        {
            "tenant_id": tenant_2_id,
        },
    ).scalar_one()

    # =========================
    # TENANT 2 - USER
    # =========================

    conn.execute(
        text("""
            INSERT INTO auth.users (
                email,
                password_hash,
                first_name,
                last_name,
                terms_accepted_at,
                terms_version,
                is_active
            )
            VALUES (
                :email,
                :password_hash,
                'Tenant 2',
                'User',
                now(),
                'v1',
                TRUE
            )
            ON CONFLICT (email)
            DO NOTHING;
        """),
        {
            "email": TENANT_2_USER_EMAIL,
            "password_hash": password_hash,
        },
    )

    user_2_id = conn.execute(
        text("""
            SELECT id
            FROM auth.users
            WHERE email = :email;
        """),
        {
            "email": TENANT_2_USER_EMAIL,
        },
    ).scalar_one()

    # =========================
    # ADMIN ROLE
    # =========================

    admin_role_id = conn.execute(
        text("""
            SELECT id
            FROM auth.roles
            WHERE code = 'admin';
        """)
    ).scalar_one()

    # =========================
    # LOCATION USER ROLES
    # =========================

    # Tenant 1 user -> Tenant 1 / Location 1
    conn.execute(
        text("""
            INSERT INTO auth.location_user_roles (
                user_id,
                location_id,
                role_id
            )
            VALUES (
                :user_id,
                :location_id,
                :role_id
            )
            ON CONFLICT (
                user_id,
                location_id,
                role_id
            )
            DO NOTHING;
        """),
        {
            "user_id": user_1_id,
            "location_id": tenant_1_location_1_id,
            "role_id": admin_role_id,
        },
    )

    # Tenant 1 user -> Tenant 1 / Location 2
    conn.execute(
        text("""
            INSERT INTO auth.location_user_roles (
                user_id,
                location_id,
                role_id
            )
            VALUES (
                :user_id,
                :location_id,
                :role_id
            )
            ON CONFLICT (
                user_id,
                location_id,
                role_id
            )
            DO NOTHING;
        """),
        {
            "user_id": user_1_id,
            "location_id": tenant_1_location_2_id,
            "role_id": admin_role_id,
        },
    )

    # Tenant 2 user -> Tenant 2 / Location 2
    conn.execute(
        text("""
            INSERT INTO auth.location_user_roles (
                user_id,
                location_id,
                role_id
            )
            VALUES (
                :user_id,
                :location_id,
                :role_id
            )
            ON CONFLICT (
                user_id,
                location_id,
                role_id
            )
            DO NOTHING;
        """),
        {
            "user_id": user_2_id,
            "location_id": tenant_2_location_2_id,
            "role_id": admin_role_id,
        },
    )

    # =========================
    # TENANT 1 - LOCATION 1 BRANDING
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.location_branding (
                location_id,
                display_name,
                primary_color,
                secondary_color
            )
            VALUES (
                :location_id,
                'Tenant 1 - Location 1',
                '#5E2BFF',
                '#E8FFC2'
            )
            ON CONFLICT (location_id)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                primary_color = EXCLUDED.primary_color,
                secondary_color = EXCLUDED.secondary_color;
        """),
        {
            "location_id": tenant_1_location_1_id,
        },
    )

    # =========================
    # TENANT 1 - LOCATION 2 BRANDING
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.location_branding (
                location_id,
                display_name,
                primary_color,
                secondary_color
            )
            VALUES (
                :location_id,
                'Tenant 1 - Location 2',
                '#7C3AED',
                '#D9F99D'
            )
            ON CONFLICT (location_id)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                primary_color = EXCLUDED.primary_color,
                secondary_color = EXCLUDED.secondary_color;
        """),
        {
            "location_id": tenant_1_location_2_id,
        },
    )

    # =========================
    # TENANT 2 - LOCATION 2 BRANDING
    # =========================

    conn.execute(
        text("""
            INSERT INTO tenancy.location_branding (
                location_id,
                display_name,
                primary_color,
                secondary_color
            )
            VALUES (
                :location_id,
                'Tenant 2 - Location 2',
                '#0369A1',
                '#FDBA74'
            )
            ON CONFLICT (location_id)
            DO UPDATE SET
                display_name = EXCLUDED.display_name,
                primary_color = EXCLUDED.primary_color,
                secondary_color = EXCLUDED.secondary_color;
        """),
        {
            "location_id": tenant_2_location_2_id,
        },
    )