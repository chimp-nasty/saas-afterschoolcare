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
        END$$;


        -- =====================================================
        -- STATUS TABLES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.booking_statuses (
            id SMALLSERIAL PRIMARY KEY,

            code VARCHAR(50) NOT NULL UNIQUE,
            label VARCHAR(100) NOT NULL,
            description TEXT,

            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );


        CREATE TABLE IF NOT EXISTS public.payment_statuses (
            id SMALLSERIAL PRIMARY KEY,

            code VARCHAR(50) NOT NULL UNIQUE,
            label VARCHAR(100) NOT NULL,
            description TEXT,

            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );


        CREATE TABLE IF NOT EXISTS public.invoice_statuses (
            id SMALLSERIAL PRIMARY KEY,

            code VARCHAR(50) NOT NULL UNIQUE,
            label VARCHAR(100) NOT NULL,
            description TEXT,

            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );


        CREATE TABLE IF NOT EXISTS public.medical_review_statuses (
            id SMALLSERIAL PRIMARY KEY,

            code VARCHAR(50) NOT NULL UNIQUE,
            label VARCHAR(100) NOT NULL,
            description TEXT,

            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );


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
        -- CHILD PROFILE
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_profile (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            dob DATE NOT NULL,

            has_medical_condition BOOLEAN NOT NULL DEFAULT FALSE,
            medical_info TEXT,

            has_allergies BOOLEAN NOT NULL DEFAULT FALSE,
            allergy_info TEXT,

            requires_medication BOOLEAN NOT NULL DEFAULT FALSE,
            medication_info TEXT,

            medical_documentation_provided BOOLEAN
                NOT NULL DEFAULT FALSE,

            medical_review_required BOOLEAN
                NOT NULL DEFAULT FALSE,

            medical_review_status_id SMALLINT
                REFERENCES public.medical_review_statuses(id),

            care_details_confirmed_at TIMESTAMPTZ,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- CHILD NOTES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_notes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,

            note TEXT NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- AUTHORISED PICKUPS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.authorized_pickup_persons (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            user_id UUID NOT NULL
                REFERENCES auth.users(id),

            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(30) NOT NULL,

            relation VARCHAR(100) NOT NULL,

            consent_confirmed_at TIMESTAMPTZ
                NOT NULL DEFAULT now(),

            consent_version VARCHAR(50)
                NOT NULL DEFAULT 'v1',

            identity_verified_at TIMESTAMPTZ,

            identity_verified_by_user_id UUID
                REFERENCES auth.users(id),

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_authorized_pickup_person
                UNIQUE (
                    child_id,
                    first_name,
                    last_name,
                    phone
                )
        );


        -- =====================================================
        -- CHILD DOCUMENTS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_documents (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            uploaded_by_user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,

            document_type VARCHAR(64) NOT NULL,
            original_filename VARCHAR(255) NOT NULL,

            storage_bucket VARCHAR(255) NOT NULL,
            storage_object_key TEXT NOT NULL,

            content_type VARCHAR(100),
            size_bytes INTEGER,

            upload_status VARCHAR(32)
                NOT NULL DEFAULT 'pending',

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT child_document_type_check
                CHECK (
                    document_type IN (
                        'medical_action_plan',
                        'asthma_action_plan',
                        'allergy_anaphylaxis_plan',
                        'medication_authorisation',
                        'other_supporting_document'
                    )
                ),

            CONSTRAINT child_document_upload_status_check
                CHECK (
                    upload_status IN (
                        'pending',
                        'uploaded',
                        'failed',
                        'deleted'
                    )
                )
        );


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


        -- =====================================================
        -- USER KIOSK PINS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.user_kiosk_pins (
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


        -- =====================================================
        -- SERVICE TYPES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.service_types (
            id SMALLSERIAL PRIMARY KEY,

            code VARCHAR(32) NOT NULL UNIQUE,
            label VARCHAR(64) NOT NULL,

            stripe_product_id VARCHAR(255),
            stripe_price_id VARCHAR(255) UNIQUE,

            is_active BOOLEAN NOT NULL DEFAULT TRUE
        );


        -- =====================================================
        -- LOCATION SERVICE DAYS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.location_service_days (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            service_date DATE NOT NULL,

            service_type_id SMALLINT NOT NULL
                REFERENCES public.service_types(id),

            is_open BOOLEAN NOT NULL DEFAULT TRUE,

            capacity INTEGER NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_location_service_day
                UNIQUE (
                    location_id,
                    service_date,
                    service_type_id
                )
        );


        -- =====================================================
        -- BOOKING GROUPS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.booking_groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            idempotency_key VARCHAR(128) NOT NULL,

            parent_id UUID NOT NULL
                REFERENCES auth.users(id),

            source VARCHAR(32),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_booking_group_parent_idempotency
                UNIQUE (
                    parent_id,
                    idempotency_key
                )
        );


        -- =====================================================
        -- BOOKINGS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.bookings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            booking_group_id UUID
                REFERENCES public.booking_groups(id),

            parent_id UUID NOT NULL
                REFERENCES auth.users(id),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id),

            location_service_day_id UUID NOT NULL
                REFERENCES public.location_service_days(id),

            booking_status_id SMALLINT NOT NULL
                REFERENCES public.booking_statuses(id),

            payment_status_id SMALLINT NOT NULL
                REFERENCES public.payment_statuses(id),

            booked_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            cancelled_at TIMESTAMPTZ,
            cancellation_reason TEXT,

            price_snapshot_cents INTEGER NOT NULL,
            currency currency_code_enum NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- BOOKING STATUS HISTORY
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.booking_status_history (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            booking_id UUID NOT NULL
                REFERENCES public.bookings(id)
                ON DELETE CASCADE,

            old_status_id SMALLINT
                REFERENCES public.booking_statuses(id),

            new_status_id SMALLINT NOT NULL
                REFERENCES public.booking_statuses(id),

            changed_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            changed_by_user_id UUID
                REFERENCES auth.users(id),

            note TEXT
        );


        -- =====================================================
        -- INVOICES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.invoices (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            parent_id UUID NOT NULL
                REFERENCES auth.users(id),

            billing_period_start DATE NOT NULL,
            billing_period_end DATE NOT NULL,

            status_id SMALLINT NOT NULL
                REFERENCES public.invoice_statuses(id),

            subtotal_cents INTEGER NOT NULL,
            discount_cents INTEGER NOT NULL DEFAULT 0,
            total_cents INTEGER NOT NULL,

            currency currency_code_enum NOT NULL,

            issued_at TIMESTAMPTZ,
            due_at TIMESTAMPTZ,
            paid_at TIMESTAMPTZ,

            stripe_customer_id VARCHAR(255),
            stripe_invoice_id VARCHAR(255),
            stripe_receipt_url TEXT,
            stripe_payment_intent_id VARCHAR(255),
            stripe_checkout_session_id VARCHAR(255),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- INVOICE BOOKING ITEMS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.invoice_booking_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            invoice_id UUID NOT NULL
                REFERENCES public.invoices(id)
                ON DELETE CASCADE,

            booking_id UUID NOT NULL
                REFERENCES public.bookings(id),

            line_description VARCHAR(255) NOT NULL,

            amount_cents INTEGER NOT NULL,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_invoice_booking_item_booking
                UNIQUE (booking_id)
        );


        -- =====================================================
        -- BOOKING REFUNDS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.booking_refunds (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            booking_id UUID NOT NULL
                REFERENCES public.bookings(id),

            invoice_id UUID NOT NULL
                REFERENCES public.invoices(id),

            invoice_booking_item_id UUID NOT NULL
                REFERENCES public.invoice_booking_items(id),

            parent_id UUID NOT NULL
                REFERENCES auth.users(id),

            requested_by_user_id UUID NOT NULL
                REFERENCES auth.users(id),

            amount_cents INTEGER NOT NULL,
            currency currency_code_enum NOT NULL,

            status VARCHAR(32)
                NOT NULL DEFAULT 'PENDING',

            reason TEXT,

            stripe_payment_intent_id VARCHAR(255) NOT NULL,
            stripe_refund_id VARCHAR(255),

            requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            processed_at TIMESTAMPTZ,
            failed_at TIMESTAMPTZ,
            failure_reason TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_booking_refund_booking
                UNIQUE (booking_id)
        );


        -- =====================================================
        -- ATTENDANCE RECORDS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.attendance_records (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            booking_id UUID NOT NULL UNIQUE
                REFERENCES public.bookings(id)
                ON DELETE CASCADE,

            signed_in_at TIMESTAMPTZ,
            signed_out_at TIMESTAMPTZ,

            signed_in_by_user_id UUID
                REFERENCES auth.users(id),

            signed_out_by_user_id UUID
                REFERENCES auth.users(id),

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT attendance_signout_requires_signin
                CHECK (
                    signed_out_at IS NULL
                    OR signed_in_at IS NOT NULL
                ),

            CONSTRAINT attendance_signout_after_signin
                CHECK (
                    signed_out_at IS NULL
                    OR signed_out_at >= signed_in_at
                )
        );
    """))