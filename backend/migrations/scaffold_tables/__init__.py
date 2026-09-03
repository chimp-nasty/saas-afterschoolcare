from sqlalchemy.engine import Connection

from . import (
    m001_create_tenancy_schema,
    m002_create_authorization_schema,
    m003_create_public_schema,
    m004_create_rls_policies,
)


def up(conn: Connection) -> None:
    m001_create_tenancy_schema.up(conn)
    m002_create_authorization_schema.up(conn)
    m003_create_public_schema.up(conn)
    m004_create_rls_policies.up(conn)