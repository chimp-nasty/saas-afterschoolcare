from sqlalchemy.engine import Connection

from . import (
    m001_seed_permissions,
    m002_seed_roles,
)


def up(conn: Connection) -> None:
    m001_seed_permissions.up(conn)
    m002_seed_roles.up(conn)