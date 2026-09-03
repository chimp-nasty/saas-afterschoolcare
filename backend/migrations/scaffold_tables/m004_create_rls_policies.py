from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    _enable_rls(conn)
    _create_booking_policies(conn)


def _enable_rls(conn: Connection) -> None:
    conn.execute(
        text("""
            ALTER TABLE public.bookings
            ENABLE ROW LEVEL SECURITY;
        """)
    )

    conn.execute(
        text("""
            ALTER TABLE public.bookings
            FORCE ROW LEVEL SECURITY;
        """)
    )


def _create_booking_policies(
    conn: Connection,
) -> None:
    conn.execute(
        text("""
            CREATE POLICY bookings_select_policy
            ON public.bookings
            FOR SELECT
            USING (
                location_id = current_setting(
                    'app.location_id',
                    true
                )::uuid
            );
        """)
    )