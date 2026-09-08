from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(
        text("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1
                    FROM pg_roles
                    WHERE rolname = 'app_user'
                ) THEN
                    CREATE ROLE app_user
                    LOGIN
                    PASSWORD 'Dev_App_User_2026!ChangeMe'
                    NOSUPERUSER
                    NOCREATEDB
                    NOCREATEROLE
                    NOINHERIT
                    NOREPLICATION
                    NOBYPASSRLS;
                END IF;
            END
            $$;
        """)
    )

    # ---------------------------------------------------------------------
    # SCHEMA ACCESS
    # ---------------------------------------------------------------------

    conn.execute(
        text("""
            GRANT USAGE
            ON SCHEMA public, auth, tenancy
            TO app_user;
        """)
    )

    # ---------------------------------------------------------------------
    # PUBLIC
    # ---------------------------------------------------------------------

    conn.execute(
        text("""
            GRANT SELECT, INSERT, UPDATE, DELETE
            ON ALL TABLES IN SCHEMA public
            TO app_user;
        """)
    )

    # ---------------------------------------------------------------------
    # AUTH
    # ---------------------------------------------------------------------

    # Read auth configuration / identity data.
    conn.execute(
        text("""
            GRANT SELECT
            ON ALL TABLES IN SCHEMA auth
            TO app_user;
        """)
    )

    # Registration and account updates.
    conn.execute(
        text("""
            GRANT INSERT, UPDATE
            ON auth.users
            TO app_user;
        """)
    )

    # Membership creation / management.
    conn.execute(
        text("""
            GRANT INSERT, UPDATE, DELETE
            ON auth.location_user_roles
            TO app_user;
        """)
    )

    # ---------------------------------------------------------------------
    # TENANCY
    # ---------------------------------------------------------------------

    conn.execute(
        text("""
            GRANT SELECT
            ON ALL TABLES IN SCHEMA tenancy
            TO app_user;
        """)
    )

    # ---------------------------------------------------------------------
    # SEQUENCES
    # ---------------------------------------------------------------------

    conn.execute(
        text("""
            GRANT USAGE, SELECT
            ON ALL SEQUENCES IN SCHEMA public, auth
            TO app_user;
        """)
    )