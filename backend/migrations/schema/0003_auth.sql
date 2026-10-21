-- =====================================================
-- USERS
-- =====================================================

CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    terms_accepted_at TIMESTAMPTZ NOT NULL,
    terms_version VARCHAR(50) NOT NULL DEFAULT 'v1',

    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login TIMESTAMPTZ,

    CONSTRAINT uq_users_email
        UNIQUE (email)
);


-- =====================================================
-- STAFF PINS
-- =====================================================

-- A staff member's 4-digit PIN for the staff kiosk, where it records who
-- did what. One per person, used at every location they work at. Set or
-- changed only on the website, after re-entering their password
-- (public.set_staff_pin); only its hash is kept. Five wrong PINs at the
-- kiosk lock it until they set a new one.
CREATE TABLE auth.staff_pins (
    user_id UUID PRIMARY KEY,

    pin_hash TEXT NOT NULL,
    failed_pin_attempts SMALLINT NOT NULL DEFAULT 0,
    pin_locked_at TIMESTAMPTZ,
    set_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_staff_pins_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT ck_staff_pins_failed_pin_attempts
        CHECK (failed_pin_attempts >= 0)
);


-- =====================================================
-- PASSWORD RESET TOKENS
-- =====================================================

-- A reset is requested at one location (the user must have a role there):
-- its emails go out as that centre, linking back to its site.
CREATE TABLE auth.password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,

    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_password_reset_tokens_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_password_reset_tokens_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_password_reset_tokens_token_hash
        UNIQUE (token_hash)
);


-- =====================================================
-- ROLES
-- =====================================================

CREATE TABLE auth.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_roles_code
        UNIQUE (code),

    CONSTRAINT ck_roles_code_format
        CHECK (code ~ '^[a-z][a-z0-9_]*$')
);


-- =====================================================
-- PERMISSIONS
-- =====================================================

CREATE TABLE auth.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resource VARCHAR(100) NOT NULL,
    action VARCHAR(1) NOT NULL,
    description TEXT,

    CONSTRAINT uq_permissions_resource_action
        UNIQUE (resource, action),

    CONSTRAINT ck_permissions_action
        CHECK (action IN ('c', 'r', 'u', 'd')),

    CONSTRAINT ck_permissions_resource_format
        CHECK (resource ~ '^[a-z][a-z0-9_]*$')
);


-- =====================================================
-- ROLE PERMISSIONS
-- =====================================================

-- A role's permission on one channel (docs/portals.md, section 2): the
-- same role can do different things on the website and at the staff kiosk.
CREATE TABLE auth.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    channel auth.permission_channel_enum NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_role_permissions_role
        FOREIGN KEY (role_id)
        REFERENCES auth.roles (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_role_permissions_permission
        FOREIGN KEY (permission_id)
        REFERENCES auth.permissions (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_role_permissions_role_permission_channel
        UNIQUE (role_id, permission_id, channel)
);


-- =====================================================
-- LOCATION USER ROLES
-- =====================================================

CREATE TABLE auth.location_user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,
    role_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_location_user_roles_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_location_user_roles_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_location_user_roles_role
        FOREIGN KEY (role_id)
        REFERENCES auth.roles (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_location_user_roles_user_location_role
        UNIQUE (user_id, location_id, role_id)
);
