from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        INSERT INTO auth.roles (
            code,
            name,
            description
        )
        VALUES
            (
                'admin',
                'Administrator',
                'Administrative user for a location.'
            ),
            (
                'staff',
                'Staff',
                'Staff user assigned to a location.'
            ),
            (
                'customer',
                'Customer',
                'Customer user assigned to a location.'
            )
        ON CONFLICT (code)
        DO UPDATE SET
            name = EXCLUDED.name,
            description = EXCLUDED.description;
    """))