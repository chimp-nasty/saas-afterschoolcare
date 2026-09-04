from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    conn.execute(text("""
        CREATE EXTENSION IF NOT EXISTS pgcrypto;
    """))

    conn.execute(text("""
        -- =====================================================
        -- ENUMS
        -- =====================================================

        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'currency_code_enum'
            ) THEN
                CREATE TYPE currency_code_enum AS ENUM (
                    'AUD',
                    'NZD',
                    'USD'
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'stripe_status_enum'
            ) THEN
                CREATE TYPE stripe_status_enum AS ENUM (
                    'PENDING',
                    'SUCCEEDED',
                    'FAILED'
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'payment_status_enum'
            ) THEN
                CREATE TYPE payment_status_enum AS ENUM (
                    'PENDING',
                    'PAID',
                    'REFUNDED',
                    'FAILED'
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'booking_status_enum'
            ) THEN
                CREATE TYPE booking_status_enum AS ENUM (
                    'PENDING',
                    'CONFIRMED',
                    'CANCELLED',
                    'EXPIRED'
                );
            END IF;
        END$$;


        -- =====================================================
        -- BOOKING GROUPS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.booking_groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            idempotency_key VARCHAR(128) NOT NULL,

            user_id UUID NOT NULL
                REFERENCES auth.users(id),

            source VARCHAR(32),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_booking_group_user_idempotency
                UNIQUE (
                    user_id,
                    idempotency_key
                )
        );


        -- =====================================================
        -- BOOKINGS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.bookings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            user_id UUID NOT NULL
                REFERENCES auth.users(id),

            booking_group_id UUID NOT NULL
                REFERENCES public.booking_groups(id),

            location_service_day_id UUID NOT NULL
                REFERENCES public.location_service_days(id),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id),

            booking_status booking_status_enum
                NOT NULL DEFAULT 'PENDING',

            payment_status payment_status_enum
                NOT NULL DEFAULT 'PENDING',

            cancelled_at TIMESTAMPTZ,

            price_snapshot_cents INTEGER NOT NULL,

            currency currency_code_enum NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE UNIQUE INDEX IF NOT EXISTS uq_active_booking_child_location_service_day
            ON public.bookings (
                child_id,
                location_service_day_id
            )
            WHERE booking_status IN (
                'PENDING',
                'CONFIRMED'
            );


        -- =====================================================
        -- PAYMENT ATTEMPTS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.payment_attempts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            user_id UUID NOT NULL
                REFERENCES auth.users(id),

            stripe_status stripe_status_enum
                NOT NULL DEFAULT 'PENDING',

            stripe_payment_intent_id VARCHAR(255) UNIQUE,

            stripe_checkout_session_id VARCHAR(255) UNIQUE,

            stripe_receipt_url TEXT,

            booking_group_id UUID NOT NULL
                REFERENCES public.booking_groups(id),

            total_cents INTEGER NOT NULL,

            currency currency_code_enum NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- REFUNDS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.refunds (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            booking_id UUID NOT NULL
                REFERENCES public.bookings(id),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            user_id UUID NOT NULL
                REFERENCES auth.users(id),

            requested_by_user_id UUID NOT NULL
                REFERENCES auth.users(id),

            reason TEXT,

            stripe_refund_id VARCHAR(255) UNIQUE,

            failed_at TIMESTAMPTZ,
            failure_reason TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            processed_at TIMESTAMPTZ
        );
    """))