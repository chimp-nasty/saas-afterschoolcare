from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """))

    conn.execute(text("""
        -- =====================================================
        -- CUSTOMER PROFILE
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.customer_profile (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,

            phone VARCHAR(30),

            address_line_1 VARCHAR(255),
            address_line_2 VARCHAR(255),
            suburb VARCHAR(100),
            state VARCHAR(100),
            postcode VARCHAR(20),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_customer_profile_user
                UNIQUE (user_id)
        );

        -- =====================================================
        -- CUSTOMER KIOSK PINS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.customer_kiosk_pins (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,

            pin_hash TEXT NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_used_at TIMESTAMPTZ,

            CONSTRAINT uq_user_kiosk_pin
                UNIQUE (user_id)
        );
    """))