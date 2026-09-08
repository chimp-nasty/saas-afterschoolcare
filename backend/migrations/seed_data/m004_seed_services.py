from sqlalchemy import text
from sqlalchemy.engine import Connection


SERVICE_TYPES = [
    {
        "code": "after_school_care",
        "name": "After School Care",
    },
    {
        "code": "before_school_care",
        "name": "Before School Care",
    },
    {
        "code": "vacation_care",
        "name": "Vacation Care",
    },
    {
        "code": "weekend_care",
        "name": "Weekend Care"
    }
]


def up(conn: Connection) -> None:
    for service in SERVICE_TYPES:
        conn.execute(
            text("""
                INSERT INTO public.service_types (
                    code,
                    name
                )
                VALUES (
                    :code,
                    :name
                )
                ON CONFLICT (code)
                DO UPDATE SET
                    name = EXCLUDED.name;
            """),
            service,
        )