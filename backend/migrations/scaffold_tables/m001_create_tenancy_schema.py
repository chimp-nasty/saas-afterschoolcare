from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE EXTENSION IF NOT EXISTS pgcrypto;

        CREATE SCHEMA IF NOT EXISTS tenancy;
    """))

    conn.execute(text("""
        -- =========================
        -- TENANTS
        -- =========================

        CREATE TABLE IF NOT EXISTS tenancy.tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            label VARCHAR(200) NOT NULL,
            code VARCHAR(50) NOT NULL UNIQUE,

            email VARCHAR(255),

            terms_accepted_at TIMESTAMPTZ NOT NULL,
            terms_version VARCHAR(50) NOT NULL DEFAULT 'v1',

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =========================
        -- LOCATIONS
        -- =========================

        CREATE TABLE IF NOT EXISTS tenancy.locations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            tenant_id UUID NOT NULL
                REFERENCES tenancy.tenants(id)
                ON DELETE CASCADE,

            name VARCHAR(200) NOT NULL,
            code VARCHAR(50) NOT NULL,

            address TEXT,
            phone VARCHAR(50),
            email VARCHAR(255),

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_location_tenant_code
                UNIQUE (tenant_id, code)
        );


        -- =========================
        -- LOCATION BRANDING
        -- =========================

        CREATE TABLE IF NOT EXISTS tenancy.location_branding (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id)
                ON DELETE CASCADE,

            display_name VARCHAR(200),

            logo_key TEXT,

            primary_color VARCHAR(50),
            secondary_color VARCHAR(50),

            font_family VARCHAR(100),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_location_branding_location
                UNIQUE (location_id)
        );
    """))