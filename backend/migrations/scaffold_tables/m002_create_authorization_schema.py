from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE SCHEMA IF NOT EXISTS authorization;
    """))

    conn.execute(text("""
        -- =========================
        -- USERS
        -- =========================

        CREATE TABLE IF NOT EXISTS authorization.users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            email VARCHAR(255) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,

            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,

            terms_accepted_at TIMESTAMPTZ NOT NULL,
            terms_version VARCHAR(50) NOT NULL DEFAULT 'v1',

            is_active BOOLEAN NOT NULL DEFAULT FALSE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_login TIMESTAMPTZ
        );


        -- =========================
        -- PASSWORD RESET TOKENS
        -- =========================

        CREATE TABLE IF NOT EXISTS authorization.password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL
                REFERENCES authorization.users(id)
                ON DELETE CASCADE,

            token_hash TEXT NOT NULL UNIQUE,

            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =========================
        -- ROLES
        -- =========================

        CREATE TABLE IF NOT EXISTS authorization.roles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            code VARCHAR(100) NOT NULL UNIQUE,
            label VARCHAR(200) NOT NULL,

            description TEXT,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT roles_code_format_check
                CHECK (code ~ '^[a-z][a-z0-9_]*$')
        );


        -- =========================
        -- PERMISSIONS
        -- =========================

        CREATE TABLE IF NOT EXISTS authorization.permissions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            resource VARCHAR(100) NOT NULL,
            action VARCHAR(1) NOT NULL,
            scope VARCHAR(1) NOT NULL,

            description TEXT,

            CONSTRAINT uq_permission_resource_action_scope
                UNIQUE (resource, action, scope),

            CONSTRAINT permissions_action_check
                CHECK (action IN ('c', 'r', 'u', 'd')),

            CONSTRAINT permissions_scope_check
                CHECK (scope IN ('s', 'l')),

            CONSTRAINT permissions_resource_format_check
                CHECK (resource ~ '^[a-z][a-z0-9_]*$')
        );


        -- =========================
        -- ROLE PERMISSIONS
        -- =========================

        CREATE TABLE IF NOT EXISTS authorization.role_permissions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            role_id UUID NOT NULL
                REFERENCES authorization.roles(id)
                ON DELETE CASCADE,

            permission_id UUID NOT NULL
                REFERENCES authorization.permissions(id)
                ON DELETE CASCADE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_role_permission
                UNIQUE (role_id, permission_id)
        );


        -- =========================
        -- LOCATION USER ROLES
        -- =========================

        CREATE TABLE IF NOT EXISTS authorization.location_user_roles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL
                REFERENCES authorization.users(id)
                ON DELETE CASCADE,

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id)
                ON DELETE CASCADE,

            role_id UUID NOT NULL
                REFERENCES authorization.roles(id)
                ON DELETE CASCADE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_location_user_role
                UNIQUE (user_id, location_id, role_id)
        );
    """))