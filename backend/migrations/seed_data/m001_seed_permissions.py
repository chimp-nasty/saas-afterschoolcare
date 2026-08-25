from itertools import product

from sqlalchemy import text
from sqlalchemy.engine import Connection


RESOURCES = [
    "user_profile",
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

SCOPES = {
    "s": "self",
    "l": "location",
}


def up(conn: Connection) -> None:
    for resource, action, scope in product(
        RESOURCES,
        ACTIONS,
        SCOPES,
    ):
        description = (
            f"{ACTIONS[action]} {resource.replace('_', ' ')} "
            f"within {SCOPES[scope]} scope."
        )

        conn.execute(
            text("""
                INSERT INTO auth.permissions (
                    resource,
                    action,
                    scope,
                    description
                )
                VALUES (
                    :resource,
                    :action,
                    :scope,
                    :description
                )
                ON CONFLICT (
                    resource,
                    action,
                    scope
                )
                DO UPDATE SET
                    description = EXCLUDED.description;
            """),
            {
                "resource": resource,
                "action": action,
                "scope": scope,
                "description": description,
            },
        )