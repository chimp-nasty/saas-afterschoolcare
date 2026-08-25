from sqlalchemy.engine import Connection

from . import (
    m001_seed_permissions,
    m003_seed_statuses,
)


def up(conn: Connection) -> None:
    m001_seed_permissions.up(conn)
    m003_seed_statuses.up(conn)