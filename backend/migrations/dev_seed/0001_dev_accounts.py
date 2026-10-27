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

# Each tenant's owner: its superadmin (business settings such as services
# and prices) and holder of its tenant permissions.
TENANT_1_SUPERADMIN_EMAIL = "sa1user@test.com"
TENANT_2_SUPERADMIN_EMAIL = "sa2user@test.com"

# The platform's own admin (the platform's site: localhost:5173/platform).
PLATFORM_ADMIN_EMAIL = "platform@test.com"


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
                address_line_1,
                suburb,
                state,
                postcode,
                email,
                is_active
            )
            VALUES (
                :tenant_id,
                'Location 1',
                'location1',
                '1 Placeholder Street',
                'Brisbane City',
                'QLD',
                '4000',
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
                address_line_1,
                suburb,
                state,
                postcode,
                email,
                is_active
            )
            VALUES (
                :tenant_id,
                'Location 2',
                'location2',
                '2 Placeholder Street',
                'Brisbane City',
                'QLD',
                '4000',
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
                address_line_1,
                suburb,
                state,
                postcode,
                email,
                is_active
            )
            VALUES (
                :tenant_id,
                'Location 2',
                'location2',
                '3 Placeholder Street',
                'Brisbane City',
                'QLD',
                '4000',
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
    # BRANDING (one per business)
    # =========================

    # Tenant 1 has the mockup's colours (docs/reference-imgs): navy, blue
    # and amber.
    for tenant_id, primary_color, secondary_color, accent_color in (
        (tenant_1_id, "#0F172A", "#2563EB", "#F59E0B"),
        (tenant_2_id, "#0369A1", "#FDBA74", "#16A34A"),
    ):
        conn.execute(
            text("""
                INSERT INTO tenancy.tenant_branding (tenant_id, primary_color, secondary_color, accent_color)
                VALUES (:tenant_id, :primary_color, :secondary_color, :accent_color)
                ON CONFLICT (tenant_id)
                DO UPDATE SET
                    primary_color = EXCLUDED.primary_color,
                    secondary_color = EXCLUDED.secondary_color,
                    accent_color = EXCLUDED.accent_color;
            """),
            {
                "tenant_id": tenant_id,
                "primary_color": primary_color,
                "secondary_color": secondary_color,
                "accent_color": accent_color,
            },
        )

    # Tenant 1's hero and highlights (docs/public-site.md), the mockup's
    # wording; tenant 2 has none, to see the pages without them.
    conn.execute(
        text("""
            UPDATE tenancy.tenants
            SET tagline = 'A welcoming place after school.',
                hero_text = 'A safe, supportive and engaging space to relax, make friends and take part in activities after school.'
            WHERE id = :tenant_id;
        """),
        {"tenant_id": tenant_1_id},
    )

    for position, (icon, title, body) in enumerate((
        ("shield", "Safe and supervised", "Qualified staff and a safe environment."),
        ("community", "A welcoming community", "Somewhere to make friends and belong."),
        ("activities", "Activities and programs", "Sport, creative, study and social activities."),
        ("location", "Convenient location", "On or near school grounds, easy to reach."),
    )):
        conn.execute(
            text("""
                INSERT INTO tenancy.tenant_highlights (tenant_id, position, icon, title, description)
                VALUES (:tenant_id, :position, :icon, :title, :description)
                ON CONFLICT (tenant_id, position) DO NOTHING;
            """),
            {"tenant_id": tenant_1_id, "position": position, "icon": icon, "title": title, "description": body},
        )

    # =========================
    # TENANT OWNERS
    # =========================
    # Each tenant's owner: superadmin at all its locations (the
    # tenant_owners trigger) and holder of every tenant permission.

    for email, first_name, tenant_id in (
        (TENANT_1_SUPERADMIN_EMAIL, "Super", tenant_1_id),
        (TENANT_2_SUPERADMIN_EMAIL, "Super Two", tenant_2_id),
    ):
        owner_id = conn.execute(
            text("""
                INSERT INTO auth.users (
                    email, password_hash, first_name, last_name,
                    terms_accepted_at, terms_version, is_active
                )
                VALUES (:email, :password_hash, :first_name, 'Admin', now(), 'v1', TRUE)
                ON CONFLICT (email) DO UPDATE SET email = EXCLUDED.email
                RETURNING id;
            """),
            {
                "email": email,
                "password_hash": password_hash,
                "first_name": first_name,
            },
        ).scalar_one()

        conn.execute(
            text("""
                INSERT INTO auth.tenant_owners (tenant_id, user_id)
                VALUES (:tenant_id, :user_id)
                ON CONFLICT (tenant_id) DO NOTHING;
            """),
            {
                "tenant_id": tenant_id,
                "user_id": owner_id,
            },
        )

        conn.execute(
            text("""
                INSERT INTO auth.user_tenant_permissions (user_id, tenant_id, permission_id)
                SELECT :user_id, :tenant_id, p.id
                FROM auth.permissions p
                WHERE p.scope = 'tenant'
                ON CONFLICT (user_id, tenant_id, permission_id) DO NOTHING;
            """),
            {
                "tenant_id": tenant_id,
                "user_id": owner_id,
            },
        )

    # =========================
    # PLATFORM ADMIN
    # =========================

    conn.execute(
        text("""
            INSERT INTO auth.platform_admins (email, password_hash, first_name, last_name)
            VALUES (:email, :password_hash, 'Platform', 'Admin')
            ON CONFLICT (email) DO NOTHING;
        """),
        {
            "email": PLATFORM_ADMIN_EMAIL,
            "password_hash": password_hash,
        },
    )
