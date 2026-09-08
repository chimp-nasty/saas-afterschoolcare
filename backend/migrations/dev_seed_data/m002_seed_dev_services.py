from datetime import date, timedelta

from sqlalchemy import text
from sqlalchemy.engine import Connection


# =========================
# DEV SERVICE CONFIG
# =========================

SERVICE_CONFIG = {
    "after_school_care": {
        "price_cents": 3000,
        "capacity": 30,
    },
    "before_school_care": {
        "price_cents": 3000,
        "capacity": 30,
    },
    "vacation_care": {
        "price_cents": 5000,
        "capacity": 30,
    },
    "weekend_care": {
        "price_cents": 6000,
        "capacity": 30,
    },
}


# =========================
# 2026 QLD SCHOOL CALENDAR
# =========================

TERM_3_START = date(2026, 7, 13)
TERM_3_END = date(2026, 9, 18)

TERM_4_START = date(2026, 10, 6)
TERM_4_END = date(2026, 12, 11)

SEED_START = TERM_3_START
SEED_END = date(2026, 12, 31)


# Staff professional development / student-free day.
STUDENT_FREE_DAYS = {
    date(2026, 9, 4),
}


# Statewide public holidays relevant to this seed period.
PUBLIC_HOLIDAYS = {
    date(2026, 10, 5),   # King's Birthday
    date(2026, 12, 25),  # Christmas Day
    date(2026, 12, 28),  # Boxing Day observed
}


# =========================
# HELPERS
# =========================

def iter_dates(
    start: date,
    end: date,
):
    current = start

    while current <= end:
        yield current
        current += timedelta(days=1)


def is_weekend(day: date) -> bool:
    return day.weekday() >= 5


def is_school_day(day: date) -> bool:
    if day in STUDENT_FREE_DAYS:
        return False

    return (
        TERM_3_START <= day <= TERM_3_END
        or TERM_4_START <= day <= TERM_4_END
    )


def get_service_code_for_day(
    day: date,
) -> str | None:
    if day in PUBLIC_HOLIDAYS:
        return None

    if is_weekend(day):
        return "weekend_care"

    if is_school_day(day):
        # School days get BOTH before and after care,
        # so handled separately.
        return None

    return "vacation_care"


def get_location_id(
    conn: Connection,
    *,
    tenant_code: str,
    location_code: str,
):
    return conn.execute(
        text("""
            SELECT l.id
            FROM tenancy.locations AS l
            JOIN tenancy.tenants AS t
                ON t.id = l.tenant_id
            WHERE
                t.code = :tenant_code
                AND l.code = :location_code;
        """),
        {
            "tenant_code": tenant_code,
            "location_code": location_code,
        },
    ).scalar_one()


def get_service_type_id(
    conn: Connection,
    *,
    service_code: str,
):
    return conn.execute(
        text("""
            SELECT id
            FROM public.service_types
            WHERE code = :service_code;
        """),
        {
            "service_code": service_code,
        },
    ).scalar_one()


def upsert_location_service(
    conn: Connection,
    *,
    location_id,
    service_type_id,
    price_cents: int,
):
    conn.execute(
        text("""
            INSERT INTO public.location_services (
                location_id,
                service_type_id,
                current_price_cents,
                currency,
                is_active
            )
            VALUES (
                :location_id,
                :service_type_id,
                :price_cents,
                'AUD',
                TRUE
            )
            ON CONFLICT (
                location_id,
                service_type_id
            )
            DO UPDATE SET
                current_price_cents =
                    EXCLUDED.current_price_cents,
                currency =
                    EXCLUDED.currency,
                is_active =
                    EXCLUDED.is_active;
        """),
        {
            "location_id": location_id,
            "service_type_id": service_type_id,
            "price_cents": price_cents,
        },
    )

    return conn.execute(
        text("""
            SELECT id
            FROM public.location_services
            WHERE
                location_id = :location_id
                AND service_type_id = :service_type_id;
        """),
        {
            "location_id": location_id,
            "service_type_id": service_type_id,
        },
    ).scalar_one()


def upsert_location_service_day(
    conn: Connection,
    *,
    location_service_id,
    service_date: date,
    capacity: int,
):
    conn.execute(
        text("""
            INSERT INTO public.location_service_days (
                location_service_id,
                service_date,
                capacity,
                is_open
            )
            VALUES (
                :location_service_id,
                :service_date,
                :capacity,
                TRUE
            )
            ON CONFLICT (
                location_service_id,
                service_date
            )
            DO UPDATE SET
                capacity = EXCLUDED.capacity,
                is_open = EXCLUDED.is_open;
        """),
        {
            "location_service_id": location_service_id,
            "service_date": service_date,
            "capacity": capacity,
        },
    )


# =========================
# SEED
# =========================

def up(conn: Connection) -> None:
    # These match seed_dev_accounts.py.
    locations = [
        ("tenant1", "location1"),
        ("tenant1", "location2"),
        ("tenant2", "location2"),
    ]

    service_type_ids = {
        service_code: get_service_type_id(
            conn,
            service_code=service_code,
        )
        for service_code in SERVICE_CONFIG
    }

    for tenant_code, location_code in locations:
        location_id = get_location_id(
            conn,
            tenant_code=tenant_code,
            location_code=location_code,
        )

        location_services = {}

        # ---------------------------------
        # LOCATION SERVICES
        # ---------------------------------

        for service_code, config in SERVICE_CONFIG.items():
            location_services[service_code] = (
                upsert_location_service(
                    conn,
                    location_id=location_id,
                    service_type_id=service_type_ids[
                        service_code
                    ],
                    price_cents=config[
                        "price_cents"
                    ],
                )
            )

        # ---------------------------------
        # LOCATION SERVICE DAYS
        # ---------------------------------

        for day in iter_dates(
            SEED_START,
            SEED_END,
        ):
            # Public holidays have no care.
            if day in PUBLIC_HOLIDAYS:
                continue

            # Weekends always use Weekend Care.
            if is_weekend(day):
                config = SERVICE_CONFIG[
                    "weekend_care"
                ]

                upsert_location_service_day(
                    conn,
                    location_service_id=location_services[
                        "weekend_care"
                    ],
                    service_date=day,
                    capacity=config["capacity"],
                )

                continue

            # School weekdays get both before and
            # after school care.
            if is_school_day(day):
                for service_code in (
                    "before_school_care",
                    "after_school_care",
                ):
                    config = SERVICE_CONFIG[
                        service_code
                    ]

                    upsert_location_service_day(
                        conn,
                        location_service_id=location_services[
                            service_code
                        ],
                        service_date=day,
                        capacity=config["capacity"],
                    )

                continue

            # Any remaining weekday is a school
            # holiday, so it gets Vacation Care.
            config = SERVICE_CONFIG[
                "vacation_care"
            ]

            upsert_location_service_day(
                conn,
                location_service_id=location_services[
                    "vacation_care"
                ],
                service_date=day,
                capacity=config["capacity"],
            )