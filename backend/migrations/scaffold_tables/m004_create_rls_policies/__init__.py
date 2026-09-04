from sqlalchemy.engine import Connection

from . import (
    m001_create_tenancy_policies,
    m002_create_auth_policies,
    m003_create_public_policies,
)


def up(conn: Connection) -> None:
    m001_create_tenancy_policies.up(conn)
    m002_create_auth_policies.up(conn)
    m003_create_public_policies.up(conn)