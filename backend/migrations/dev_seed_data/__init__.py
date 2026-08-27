from sqlalchemy.engine import Connection

from . import (
    m001_seed_dev_accounts,
)


def up(conn: Connection) -> None:
    m001_seed_dev_accounts.up(conn)
