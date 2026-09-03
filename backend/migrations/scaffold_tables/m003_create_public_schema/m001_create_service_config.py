from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """))

    conn.execute(text("""
        -- =====================================================
        -- SERVICE TYPES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.service_types (
            id SMALLSERIAL PRIMARY KEY,

            code VARCHAR(32) NOT NULL UNIQUE,
            name VARCHAR(64) NOT NULL
        );

        -- =====================================================
        -- LOCATION SERVICE TYPES
        -- =====================================================
        CREATE TABLE IF NOT EXISTS public.location_services (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            service_type_id SMALLINT NOT NULL
                REFERENCES public.service_types(id),

            stripe_product_id VARCHAR(255) UNIQUE,
            stripe_price_id VARCHAR(255) UNIQUE,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (
                location_id,
                service_type_id
            )
        );

        -- =====================================================
        -- LOCATION SERVICE DAYS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.location_service_days (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_service_id UUID NOT NULL
                REFERENCES public.location_services(id),

            service_date DATE NOT NULL,

            is_open BOOLEAN NOT NULL DEFAULT TRUE,
            capacity INTEGER NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            UNIQUE (
                location_service_id,
                service_date
            )
        );
    """))