from sqlalchemy.engine import Connection

from . import (
    m001_seed_dev_accounts,
    m002_seed_dev_services,
    m003_seed_customer,
)


def up(conn: Connection) -> None:
    m001_seed_dev_accounts.up(conn)
    m002_seed_dev_services.up(conn)
    m003_seed_customer.up(conn)
