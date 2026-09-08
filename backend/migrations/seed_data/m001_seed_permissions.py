from itertools import product

from sqlalchemy import text
from sqlalchemy.engine import Connection


RESOURCES = [
    "attendance_records",
    "authorized_pickup_persons",
    "booking_groups",
    "bookings",
    "child_documents",
    "child_medical_reviews",
    "child_medical_state",
    "child_notes",
    "child_profile",
    "customer_kiosk_pins",
    "customer_profile",
    "location_kiosk_devices",
    "location_service_days",
    "location_services",
    "payment_attempts",
    "refunds",
    "service_types",
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