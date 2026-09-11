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

    # =========================
    # ACTION CREATOR
    # =========================

    created_by_user_id = conn.execute(
        text("""
            SELECT lur.user_id
            FROM auth.location_user_roles lur
            JOIN auth.roles r
                ON r.id = lur.role_id
            WHERE
                lur.location_id = :location_id
                AND r.code IN (
                    'staff',
                    'admin',
                    'superadmin'
                )
            ORDER BY
                CASE r.code
                    WHEN 'staff' THEN 1
                    WHEN 'admin' THEN 2
                    WHEN 'superadmin' THEN 3
                END
            LIMIT 1;
        """),
        {
            "location_id": location_id,
        },
    ).scalar_one_or_none()

    # Development fallback if this seed runs before a staff user exists.
    if created_by_user_id is None:
        created_by_user_id = user_id

    # =========================
    # ACTION 1 - CHILD PROFILE
    # =========================

    conn.execute(
        text("""
            INSERT INTO public.actions (
                user_id,
                child_id,
                target,
                title,
                message,
                created_by_user_id
            )
            SELECT
                :user_id,
                :child_id,
                'profile',
                'Review Emma''s profile',
                'Please review Emma''s profile information and make sure it is up to date.',
                :created_by_user_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.actions
                WHERE
                    user_id = :user_id
                    AND child_id = :child_id
                    AND target = 'profile'
                    AND title = 'Review Emma''s profile'
            );
        """),
        {
            "user_id": user_id,
            "child_id": emma_id,
            "created_by_user_id": created_by_user_id,
        },
    )

    # =========================
    # ACTION 2 - CHILD DOCUMENTS
    # =========================

    conn.execute(
        text("""
            INSERT INTO public.actions (
                user_id,
                child_id,
                target,
                title,
                message,
                created_by_user_id
            )
            SELECT
                :user_id,
                :child_id,
                'manage-documents',
                'Upload medical documentation',
                'Please upload the requested medical documentation for Emma.',
                :created_by_user_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.actions
                WHERE
                    user_id = :user_id
                    AND child_id = :child_id
                    AND target = 'manage-documents'
                    AND title = 'Upload medical documentation'
            );
        """),
        {
            "user_id": user_id,
            "child_id": emma_id,
            "created_by_user_id": created_by_user_id,
        },
    )

    # =========================
    # ACTION 3 - ACCOUNT PROFILE
    # =========================

    conn.execute(
        text("""
            INSERT INTO public.actions (
                user_id,
                child_id,
                target,
                title,
                message,
                created_by_user_id
            )
            SELECT
                :user_id,
                NULL,
                'profile',
                'Review your account details',
                'Please review your contact and address details and update anything that has changed.',
                :created_by_user_id
            WHERE NOT EXISTS (
                SELECT 1
                FROM public.actions
                WHERE
                    user_id = :user_id
                    AND child_id IS NULL
                    AND target = 'profile'
                    AND title = 'Review your account details'
            );
        """),
        {
            "user_id": user_id,
            "created_by_user_id": created_by_user_id,
        },
    )