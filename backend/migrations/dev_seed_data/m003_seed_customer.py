from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.security import hash_password


CUSTOMER_EMAIL = "c1user@test.com"
CUSTOMER_PASSWORD = "123"


def up(conn: Connection) -> None:
    password_hash = hash_password(
        password=CUSTOMER_PASSWORD
    )

    # =========================
    # LOCATION
    # =========================

    location_id = conn.execute(
        text("""
            SELECT l.id
            FROM tenancy.locations AS l
            JOIN tenancy.tenants AS t
                ON t.id = l.tenant_id
            WHERE
                t.code = 'tenant1'
                AND l.code = 'location1';
        """)
    ).scalar_one()

    # =========================
    # CUSTOMER ROLE
    # =========================

    customer_role_id = conn.execute(
        text("""
            SELECT id
            FROM auth.roles
            WHERE code = 'customer';
        """)
    ).scalar_one()

    # =========================
    # USER
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
                'Customer',
                'One',
                now(),
                'v1',
                TRUE
            )
            ON CONFLICT (email)
            DO NOTHING;
        """),
        {
            "email": CUSTOMER_EMAIL,
            "password_hash": password_hash,
        },
    )

    user_id = conn.execute(
        text("""
            SELECT id
            FROM auth.users
            WHERE email = :email;
        """),
        {
            "email": CUSTOMER_EMAIL,
        },
    ).scalar_one()

    # =========================
    # LOCATION USER ROLE
    # =========================

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
            "user_id": user_id,
            "location_id": location_id,
            "role_id": customer_role_id,
        },
    )

    # =========================
    # CUSTOMER PROFILE
    # =========================

    conn.execute(
        text("""
            INSERT INTO public.customer_profile (
                user_id
            )
            VALUES (
                :user_id
            )
            ON CONFLICT (user_id)
            DO NOTHING;
        """),
        {
            "user_id": user_id,
        },
    )

    # =========================
    # CHILD 1
    # =========================

    conn.execute(
        text("""
            INSERT INTO public.child_profile (
                location_id,
                user_id,
                first_name,
                last_name,
                dob,
                is_active
            )
            SELECT
                :location_id,
                :user_id,
                'Emma',
                'Test',
                DATE '2018-05-14',
                TRUE
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.child_profile
                WHERE
                    user_id = :user_id
                    AND location_id = :location_id
                    AND first_name = 'Emma'
                    AND last_name = 'Test'
            );
        """),
        {
            "location_id": location_id,
            "user_id": user_id,
        },
    )

    emma_id = conn.execute(
        text("""
            SELECT id
            FROM public.child_profile
            WHERE
                user_id = :user_id
                AND location_id = :location_id
                AND first_name = 'Emma'
                AND last_name = 'Test';
        """),
        {
            "location_id": location_id,
            "user_id": user_id,
        },
    ).scalar_one()

    conn.execute(
        text("""
            INSERT INTO public.child_medical_state (
                child_id,
                review_status
            )
            VALUES (
                :child_id,
                'not_required'
            )
            ON CONFLICT (child_id)
            DO NOTHING;
        """),
        {
            "child_id": emma_id,
        },
    )

    # =========================
    # CHILD 2
    # =========================

    conn.execute(
        text("""
            INSERT INTO public.child_profile (
                location_id,
                user_id,
                first_name,
                last_name,
                dob,
                is_active
            )
            SELECT
                :location_id,
                :user_id,
                'Noah',
                'Test',
                DATE '2020-08-22',
                TRUE
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.child_profile
                WHERE
                    user_id = :user_id
                    AND location_id = :location_id
                    AND first_name = 'Noah'
                    AND last_name = 'Test'
            );
        """),
        {
            "location_id": location_id,
            "user_id": user_id,
        },
    )

    noah_id = conn.execute(
        text("""
            SELECT id
            FROM public.child_profile
            WHERE
                user_id = :user_id
                AND location_id = :location_id
                AND first_name = 'Noah'
                AND last_name = 'Test';
        """),
        {
            "location_id": location_id,
            "user_id": user_id,
        },
    ).scalar_one()

    conn.execute(
        text("""
            INSERT INTO public.child_medical_state (
                child_id,
                review_status
            )
            VALUES (
                :child_id,
                'not_required'
            )
            ON CONFLICT (child_id)
            DO NOTHING;
        """),
        {
            "child_id": noah_id,
        },
    )