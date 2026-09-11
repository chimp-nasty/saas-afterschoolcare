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
    # ACTIONS
    # =========================

    actions = (
        (
            emma_id,
            "profile",
            "Review Emma's profile",
            "Please review Emma's profile information and make sure it is up to date.",
        ),
        (
            emma_id,
            "manage-documents",
            "Upload medical documentation",
            "Please upload the requested medical documentation for Emma.",
        ),
        (
            None,
            "profile",
            "Review your account details",
            "Please review your contact and address details and update anything that has changed.",
        ),
        (
            noah_id,
            "profile",
            "Review Noah's profile",
            "Please check Noah's profile information and confirm the details are correct.",
        ),
        (
            noah_id,
            "manage-documents",
            "Upload documentation for Noah",
            "Please upload the requested documentation for Noah.",
        ),
        (
            emma_id,
            "authorized-pickups",
            "Review Emma's pickup contacts",
            "Please review the authorized pickup contacts listed for Emma.",
        ),
        (
            noah_id,
            "authorized-pickups",
            "Review Noah's pickup contacts",
            "Please review the authorized pickup contacts listed for Noah.",
        ),
        (
            emma_id,
            "manage-documents",
            "Additional document required",
            "Please upload the additional document requested by staff for Emma.",
        ),
        (
            emma_id,
            "profile",
            "Confirm Emma's details",
            "Please confirm Emma's personal details are still current.",
        ),
        (
            noah_id,
            "profile",
            "Confirm Noah's details",
            "Please confirm Noah's personal details are still current.",
        ),
        (
            None,
            "profile",
            "Check your phone number",
            "Please confirm that the phone number on your account is current.",
        ),
        (
            None,
            "profile",
            "Check your address",
            "Please review the address saved against your account.",
        ),
        (
            emma_id,
            "authorized-pickups",
            "Confirm pickup arrangements",
            "Please confirm Emma's current authorized pickup arrangements.",
        ),
        (
            noah_id,
            "authorized-pickups",
            "Confirm pickup arrangements for Noah",
            "Please confirm Noah's current authorized pickup arrangements.",
        ),
        (
            emma_id,
            "manage-documents",
            "Review requested documents",
            "Staff have requested that you review Emma's uploaded documents.",
        ),
        (
            noah_id,
            "manage-documents",
            "Review requested documents for Noah",
            "Staff have requested that you review Noah's uploaded documents.",
        ),
        (
            emma_id,
            "profile",
            "Profile information requires attention",
            "A staff member has asked you to review Emma's profile.",
        ),
        (
            noah_id,
            "profile",
            "Profile information requires attention",
            "A staff member has asked you to review Noah's profile.",
        ),
        (
            None,
            "profile",
            "Review contact information",
            "Please check that your contact information is complete and current.",
        ),
        (
            emma_id,
            "manage-documents",
            "Medical documentation follow-up",
            "Please review the latest documentation request for Emma.",
        ),
    )

    for child_id, target, title, message in actions:
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
                    :target,
                    :title,
                    :message,
                    :created_by_user_id
                WHERE NOT EXISTS (
                    SELECT 1
                    FROM public.actions
                    WHERE
                        user_id = :user_id
                        AND child_id IS NOT DISTINCT FROM :child_id
                        AND target = :target
                        AND title = :title
                        AND message = :message
                );
            """),
            {
                "user_id": user_id,
                "child_id": child_id,
                "target": target,
                "title": title,
                "message": message,
                "created_by_user_id": created_by_user_id,
            },
        )