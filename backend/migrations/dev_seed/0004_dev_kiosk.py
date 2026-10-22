"""
Dev data for trying the kiosks at tenant1 / location1 (docs/kiosk-procedures.md):

* s1user@test.com: a staff member (password 123), staff kiosk PIN 1357.
  The admin (t1user@test.com) gets staff PIN 1357 too.
* c1user@test.com (the dev customer) gets a mobile, 0400 000 001, so they're
  on their own pickup list, with kiosk PIN 1234. They're NOT approved yet,
  so a staff member has to check their ID before they can collect.
* "Gran Test" (0400 000 002, kiosk PIN 1234) is on the family's pickup list
  and already approved, so she can collect straight away.
* Emma and Noah are booked (confirmed and paid) into every session at
  location1 on the day the seed runs (the location's date): before and
  after school care on a school day, vacation or weekend care otherwise.
  Rebuild the dev database to get bookings for a new "today".
* Every location's kiosk service times are switched OFF, so the kiosks can
  be tried at any hour. Tick the service times box on /admin/kiosks to try
  the rule.

Bookings can only be made for later days (trg_bookings_enforce_rules runs on
insert), so each is made on the next later day of the same service, then
moved to today.
"""

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.security import hash_password


STAFF_EMAIL = "s1user@test.com"
STAFF_PASSWORD = "123"
STAFF_PIN = "1357"

CUSTOMER_EMAIL = "c1user@test.com"
CUSTOMER_PHONE = "0400000001"
FAMILY_PIN = "1234"

GRAN_PHONE = "0400000002"
GRAN_EMAIL = "gran@test.com"


def up(conn: Connection) -> None:
    location_id = conn.execute(
        text("""
            SELECT l.id
            FROM tenancy.locations l
            JOIN tenancy.tenants t ON t.id = l.tenant_id
            WHERE t.code = 'tenant1' AND l.code = 'location1';
        """)
    ).scalar_one()

    # =========================
    # STAFF MEMBER
    # =========================

    conn.execute(
        text("""
            INSERT INTO auth.users (
                email, password_hash, first_name, last_name,
                terms_accepted_at, terms_version, is_active
            )
            VALUES (:email, :password_hash, 'Staff', 'One', now(), 'v1', TRUE)
            ON CONFLICT (email) DO NOTHING;
        """),
        {"email": STAFF_EMAIL, "password_hash": hash_password(password=STAFF_PASSWORD)},
    )

    conn.execute(
        text("""
            INSERT INTO auth.location_user_roles (user_id, location_id, role_id)
            SELECT u.id, :location_id, r.id
            FROM auth.users u, auth.roles r
            WHERE u.email = :email AND r.code = 'staff'
            ON CONFLICT (user_id, location_id, role_id) DO NOTHING;
        """),
        {"email": STAFF_EMAIL, "location_id": location_id},
    )

    # Kiosks usable at any hour in dev (switch it on at /admin/kiosks).
    conn.execute(text("UPDATE tenancy.locations SET kiosk_enforce_service_times = FALSE;"))

    # Staff kiosk PINs for the staff member and the admin.
    conn.execute(
        text("""
            INSERT INTO auth.staff_pins (user_id, pin_hash)
            SELECT u.id, crypt(:pin, gen_salt('bf'))
            FROM auth.users u
            WHERE u.email IN (:staff_email, 't1user@test.com')
            ON CONFLICT (user_id) DO UPDATE SET pin_hash = EXCLUDED.pin_hash;
        """),
        {"pin": STAFF_PIN, "staff_email": STAFF_EMAIL},
    )

    # =========================
    # THE FAMILY'S PICKUP LIST
    # =========================

    customer_id = conn.execute(
        text("SELECT id FROM auth.users WHERE email = :email;"),
        {"email": CUSTOMER_EMAIL},
    ).scalar_one()

    # A profile phone puts the account holder on their pickup list
    # (trg_customer_profile_account_holder_pickup).
    conn.execute(
        text("""
            UPDATE public.customer_profile
            SET phone = :phone,
                address_line_1 = COALESCE(address_line_1, '1 Test Street'),
                suburb = COALESCE(suburb, 'Brisbane City'),
                state = COALESCE(state, 'QLD'),
                postcode = COALESCE(postcode, '4000'),
                -- Booking needs an emergency contact (not a pickup person,
                -- and not the parent's own number).
                emergency_contact_name = 'Robin Neighbour',
                emergency_contact_phone = '0400999888',
                emergency_contact_relation = 'neighbour'
            WHERE user_id = :user_id;
        """),
        {"phone": CUSTOMER_PHONE, "user_id": customer_id},
    )

    conn.execute(
        text("""
            INSERT INTO public.authorized_pickup_persons (
                user_id, location_id, tenant_id, first_name, last_name, phone, email,
                relation, consent_confirmed_at, adult_confirmed_at, staff_approved_at
            )
            SELECT :user_id, l.id, l.tenant_id, 'Gran', 'Test', :phone, :email,
                   'grandparent', now(), now(), now()
            FROM tenancy.locations l
            WHERE l.id = :location_id
              AND NOT EXISTS (
                  SELECT 1 FROM public.authorized_pickup_persons
                  WHERE user_id = :user_id AND phone = :phone AND is_active
              );
        """),
        {"user_id": customer_id, "location_id": location_id, "phone": GRAN_PHONE, "email": GRAN_EMAIL},
    )

    # Known kiosk PINs (no session here, so the PIN fields can be set).
    conn.execute(
        text("""
            UPDATE public.authorized_pickup_persons
            SET pin_hash = crypt(:pin, gen_salt('bf')),
                pin_change_required = FALSE,
                pin_issued_at = now(),
                failed_pin_attempts = 0,
                pin_locked_at = NULL
            WHERE user_id = :user_id
              AND location_id = :location_id
              AND is_active;
        """),
        {"pin": FAMILY_PIN, "user_id": customer_id, "location_id": location_id},
    )

    # =========================
    # TODAY'S BOOKINGS
    # =========================

    children = conn.execute(
        text("""
            SELECT id, first_name
            FROM public.child_profile
            WHERE user_id = :user_id AND location_id = :location_id AND is_active
            ORDER BY first_name;
        """),
        {"user_id": customer_id, "location_id": location_id},
    ).all()

    # Every session at the location today, and the next later day of the
    # same service to make the booking on before moving it.
    sessions = conn.execute(
        text("""
            SELECT today.id AS today_id,
                   (
                       SELECT later.id
                       FROM public.location_service_days later
                       WHERE later.location_service_id = today.location_service_id
                         AND later.service_date > today.service_date
                         AND later.is_open
                       ORDER BY later.service_date
                       LIMIT 1
                   ) AS later_id,
                   lsc.current_price_cents,
                   lsc.currency
            FROM public.location_service_days today
            JOIN tenancy.locations l ON l.id = today.location_id
            JOIN public.location_service_config lsc
                ON lsc.location_service_id = today.location_service_id
            WHERE today.location_id = :location_id
              AND today.service_date = (now() AT TIME ZONE l.timezone)::date
              AND today.is_open;
        """),
        {"location_id": location_id},
    ).all()

    for session in sessions:
        if session.later_id is None:
            continue

        for child in children:
            key = f"dev-today-{child.id}-{session.today_id}"

            group_id = conn.execute(
                text("""
                    INSERT INTO public.booking_groups (idempotency_key, user_id, location_id, source)
                    VALUES (:key, :user_id, :location_id, 'dev_seed')
                    RETURNING id;
                """),
                {"key": key, "user_id": customer_id, "location_id": location_id},
            ).scalar_one()

            conn.execute(
                text("""
                    INSERT INTO public.payment_attempts (
                        location_id, user_id, booking_group_id, stripe_status,
                        total_cents, currency, paid_at
                    )
                    VALUES (:location_id, :user_id, :group_id, 'SUCCEEDED', :price, :currency, now());
                """),
                {
                    "location_id": location_id,
                    "user_id": customer_id,
                    "group_id": group_id,
                    "price": session.current_price_cents,
                    "currency": session.currency,
                },
            )

            booking_id = conn.execute(
                text("""
                    INSERT INTO public.bookings (
                        location_id, user_id, booking_group_id, location_service_day_id, child_id,
                        booking_status, payment_status, price_snapshot_cents, currency
                    )
                    VALUES (
                        :location_id, :user_id, :group_id, :later_id, :child_id,
                        'CONFIRMED', 'PAID', :price, :currency
                    )
                    RETURNING id;
                """),
                {
                    "location_id": location_id,
                    "user_id": customer_id,
                    "group_id": group_id,
                    "later_id": session.later_id,
                    "child_id": child.id,
                    "price": session.current_price_cents,
                    "currency": session.currency,
                },
            ).scalar_one()

            conn.execute(
                text("UPDATE public.bookings SET location_service_day_id = :today_id WHERE id = :id;"),
                {"today_id": session.today_id, "id": booking_id},
            )
