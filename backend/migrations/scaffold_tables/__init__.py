from sqlalchemy.engine import Connection

from . import (
    m001_create_tenancy_schema,
    m002_create_authorization_schema,
    m003_create_public_schema,
)


def up(conn: Connection) -> None:
    m001_create_tenancy_schema.up(conn)
    m002_create_authorization_schema.up(conn)
    m003_create_public_schema.up(conn)