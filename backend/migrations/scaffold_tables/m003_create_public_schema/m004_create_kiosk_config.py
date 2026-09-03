from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """))

    conn.execute(text("""
        -- =====================================================
        -- LOCATION KIOSK DEVICES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.location_kiosk_devices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            name TEXT NOT NULL,

            setup_secret_hash TEXT,

            token_version INTEGER NOT NULL DEFAULT 1,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            paired_at TIMESTAMPTZ,
            last_used TIMESTAMPTZ
        );
    """))