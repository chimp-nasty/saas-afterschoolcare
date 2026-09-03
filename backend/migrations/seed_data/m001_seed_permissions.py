from itertools import product

from sqlalchemy import text
from sqlalchemy.engine import Connection


RESOURCES = [
    "customer_profile",
    "child_profile",
    "child_notes",
    "authorized_pickup_persons",
    "child_documents",
    "location_kiosk_devices",
    "user_kiosk_pins",
    "location_service_days",
    "booking_groups",
    "bookings",
    "booking_status_history",
    "invoices",
    "invoice_booking_items",
    "booking_refunds",
    "attendance_records",
]

ACTIONS = {
    "c": "Create",
    "r": "Read",
    "u": "Update",
    "d": "Delete",
}


def up(conn: Connection) -> None:
    for resource, action in product(
        RESOURCES,
        ACTIONS,
    ):
        description = (
            f"{ACTIONS[action]} {resource.replace('_', ' ')}"
        )

        conn.execute(
            text("""
                INSERT INTO auth.permissions (
                    resource,
                    action,
                    description
                )
                VALUES (
                    :resource,
                    :action,
                    :description
                )
                ON CONFLICT (
                    resource,
                    action
                )
                DO UPDATE SET
                    description = EXCLUDED.description;
            """),
            {
                "resource": resource,
                "action": action,
                "description": description,
            },
        )