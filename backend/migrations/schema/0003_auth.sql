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
-- PASSWORD RESET TOKENS
-- =====================================================

CREATE TABLE auth.password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_password_reset_tokens_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
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

CREATE TABLE auth.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_role_permissions_role
        FOREIGN KEY (role_id)
        REFERENCES auth.roles (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_role_permissions_permission
        FOREIGN KEY (permission_id)
        REFERENCES auth.permissions (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_role_permissions_role_permission
        UNIQUE (role_id, permission_id)
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
