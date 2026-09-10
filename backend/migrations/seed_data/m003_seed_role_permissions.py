from sqlalchemy import text
from sqlalchemy.engine import Connection


ROLE_PERMISSIONS = {
    "superadmin": [
        ("actions", "c"),
        ("actions", "r"),
        ("actions", "u"),
        ("actions", "d"),        

        ("customer_profile", "r"),
        ("customer_profile", "u"),

        ("child_profile", "c"),
        ("child_profile", "r"),
        ("child_profile", "u"),

        ("child_notes", "c"),
        ("child_notes", "r"),
        ("child_notes", "u"),
        ("child_notes", "d"),

        ("authorized_pickup_persons", "c"),
        ("authorized_pickup_persons", "r"),
        ("authorized_pickup_persons", "u"),
        ("authorized_pickup_persons", "d"),

        ("child_documents", "c"),
        ("child_documents", "r"),
        ("child_documents", "u"),

        ("child_medical_state", "r"),
        ("child_medical_state", "u"),

        ("child_medical_reviews", "c"),
        ("child_medical_reviews", "r"),

        ("service_types", "r"),

        ("location_services", "r"),
        ("location_services", "u"),

        ("location_service_days", "c"),
        ("location_service_days", "r"),
        ("location_service_days", "u"),
        ("location_service_days", "d"),

        ("booking_groups", "r"),

        ("bookings", "r"),
        ("bookings", "u"),

        ("payment_attempts", "r"),

        ("refunds", "c"),
        ("refunds", "r"),

        ("attendance_records", "c"),
        ("attendance_records", "r"),
        ("attendance_records", "u"),

        ("location_kiosk_devices", "c"),
        ("location_kiosk_devices", "r"),
        ("location_kiosk_devices", "u"),
        ("location_kiosk_devices", "d"),

        ("customer_kiosk_pins", "r"),
        ("customer_kiosk_pins", "u"),
    ],

    "admin": [
        ("actions", "c"),
        ("actions", "r"),
        ("actions", "u"),
        ("actions", "d"),        

        ("customer_profile", "r"),
        ("customer_profile", "u"),

        ("child_profile", "c"),
        ("child_profile", "r"),
        ("child_profile", "u"),

        ("child_notes", "c"),
        ("child_notes", "r"),
        ("child_notes", "u"),
        ("child_notes", "d"),

        ("authorized_pickup_persons", "c"),
        ("authorized_pickup_persons", "r"),
        ("authorized_pickup_persons", "u"),
        ("authorized_pickup_persons", "d"),

        ("child_documents", "c"),
        ("child_documents", "r"),
        ("child_documents", "u"),

        ("child_medical_state", "r"),
        ("child_medical_state", "u"),

        ("child_medical_reviews", "c"),
        ("child_medical_reviews", "r"),

        ("service_types", "r"),

        ("location_services", "r"),
        ("location_services", "u"),

        ("location_service_days", "c"),
        ("location_service_days", "r"),
        ("location_service_days", "u"),
        ("location_service_days", "d"),

        ("booking_groups", "r"),

        ("bookings", "r"),
        ("bookings", "u"),

        ("payment_attempts", "r"),

        ("refunds", "c"),
        ("refunds", "r"),

        ("attendance_records", "c"),
        ("attendance_records", "r"),
        ("attendance_records", "u"),

        ("location_kiosk_devices", "c"),
        ("location_kiosk_devices", "r"),
        ("location_kiosk_devices", "u"),
        ("location_kiosk_devices", "d"),

        ("customer_kiosk_pins", "r"),
        ("customer_kiosk_pins", "u"),
    ],

    "staff": [
        ("actions", "c"),
        ("actions", "r"),
        ("actions", "u"),

        ("customer_profile", "r"),
        ("child_profile", "r"),

        ("child_notes", "c"),
        ("child_notes", "r"),
        ("child_notes", "u"),

        ("authorized_pickup_persons", "r"),

        ("child_documents", "r"),

        ("child_medical_state", "r"),
        ("child_medical_state", "u"),

        ("child_medical_reviews", "c"),
        ("child_medical_reviews", "r"),

        ("service_types", "r"),
        ("location_services", "r"),
        ("location_service_days", "r"),

        ("booking_groups", "r"),
        ("bookings", "r"),
        ("bookings", "u"),

        ("attendance_records", "c"),
        ("attendance_records", "r"),
        ("attendance_records", "u"),

        ("location_kiosk_devices", "r"),
        ("customer_kiosk_pins", "r"),
    ],

    "customer": [
        ("actions", "r"),
        ("actions", "u"),

        ("customer_profile", "r"),
        ("customer_profile", "u"),

        ("child_profile", "c"),
        ("child_profile", "r"),
        ("child_profile", "u"),

        ("authorized_pickup_persons", "c"),
        ("authorized_pickup_persons", "r"),
        ("authorized_pickup_persons", "u"),
        ("authorized_pickup_persons", "d"),

        ("child_documents", "c"),
        ("child_documents", "r"),
        ("child_documents", "u"),

        ("child_medical_state", "r"),
        ("child_medical_reviews", "r"),

        ("service_types", "r"),
        ("location_services", "r"),
        ("location_service_days", "r"),

        ("booking_groups", "c"),
        ("booking_groups", "r"),

        ("bookings", "c"),
        ("bookings", "r"),
        ("bookings", "u"),

        ("payment_attempts", "r"),

        ("refunds", "c"),
        ("refunds", "r"),

        ("attendance_records", "r"),

        ("customer_kiosk_pins", "r"),
        ("customer_kiosk_pins", "u"),
    ],
}

def up(conn: Connection) -> None:
    for role_code, permissions in ROLE_PERMISSIONS.items():
        for resource, action in permissions:
            conn.execute(
                text("""
                    INSERT INTO auth.role_permissions (
                        role_id,
                        permission_id
                    )
                    SELECT
                        r.id,
                        p.id
                    FROM auth.roles AS r
                    JOIN auth.permissions AS p
                        ON p.resource = :resource
                        AND p.action = :action
                    WHERE r.code = :role_code
                    ON CONFLICT (
                        role_id,
                        permission_id
                    )
                    DO NOTHING;
                """),
                {
                    "role_code": role_code,
                    "resource": resource,
                    "action": action,
                },
            )