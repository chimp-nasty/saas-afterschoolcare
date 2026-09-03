from sqlalchemy.engine import Connection

from . import (
    m001_create_service_config,
    m002_create_customer_config,
    m003_create_child_config,
    m004_create_kiosk_config,
    m005_create_booking_config,
    m006_create_attendance_config
)


def up(conn: Connection) -> None:
    m001_create_service_config.up(conn)
    m002_create_customer_config.up(conn)
    m003_create_child_config.up(conn)
    m004_create_kiosk_config.up(conn)
    m005_create_booking_config.up(conn)
    m006_create_attendance_config.up(conn)