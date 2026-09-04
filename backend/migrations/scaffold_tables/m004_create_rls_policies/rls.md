## ROLE SCOPE MATRIX
| Role | Tenant | Location | Own |
|---|---|---|---|
| superadmin | tenant configuration | all assigned locations | yes |
| admin | — | entire assigned location | yes |
| staff | — | entire assigned location | yes |
| customer | — | assigned location | own rows only |

## TENANCY
# GLOBAL / NO ROW SCOPE
These are required before authentication or are public business information.
- locations
- location_branding

# TENANT-SCOPED
- tenants
Scope:
- superadmin only
- derived by joining user_location_roles -> locations -> tenant


## AUTH
# GLOBAL / NO ROW SCOPE
These rows do not contain rls as special cases.
- location_user_roles
- password_reset_tokens

These are application configuration and don't contain tenant-specific data.
- roles
- permissions
- role_permissions

# USER + LOCATION
- users
Scope:
- customer:     self
- staff:        self, customer assigned location
- admin:        self, staff, customer assigned location
- superadmin:   self, admin, staff, customer assigned location


## PUBLIC
# GLOBAL / NO ROW SCOPE
- service_types

# USER-OWNED
- customer_kiosk_pins
- booking_groups
Scope:
- owner

# LOCATION-SCOPED
- location_services
- location_service_days
- location_kiosk_devices
Scope:
- anyone with user_location_role for location

# USER + LOCATION SCOPED
- child_profile
- bookings
- payment_attempts
- refunds
Scope:
- customer:     self
- staff:        all customers at location
- admin:        all customers at location
- superadmin:   all customers at location

# INHERITED FROM CHILD_PROFILE
- child_medical_state
- child_medical_reviews
- child_notes
- child_documents
- authorized_pickup_persons
Scope:
- derived through child_profile

# INHERITED FROM BOOKINGS
- attendance_records
Scope:
- derived through bookings

# INHERITED FROM USERS
- customer_profiles
Scope:
- derived through users