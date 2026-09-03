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
                WHERE typname = 'medical_review_status_enum'
            ) THEN
                CREATE TYPE medical_review_status_enum AS ENUM (
                    'not_required',
                    'pending',
                    'documentation_requested',
                    'approved'
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'child_document_type_enum'
            ) THEN
                CREATE TYPE child_document_type_enum AS ENUM (
                    'medical_action_plan',
                    'asthma_action_plan',
                    'allergy_anaphylaxis_plan',
                    'other'
                );
            END IF;

            IF NOT EXISTS (
                SELECT 1
                FROM pg_type
                WHERE typname = 'child_document_upload_status_enum'                        
            ) THEN
                CREATE TYPE child_document_upload_status_enum AS ENUM (
                    'pending',
                    'uploaded',
                    'failed'
                );
            END IF;
        END$$;

        -- =====================================================
        -- CHILD PROFILE
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_profile (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            location_id UUID NOT NULL
                REFERENCES tenancy.locations(id),

            user_id UUID NOT NULL
                REFERENCES auth.users(id)
                ON DELETE CASCADE,

            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            dob DATE NOT NULL,

            medical_info TEXT,
            allergy_info TEXT,
            medication_info TEXT,

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- CHILD MEDICAL STATE
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_medical_state (
            child_id UUID PRIMARY KEY
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            review_status medical_review_status_enum
                NOT NULL DEFAULT 'not_required',

            updated_at TIMESTAMPTZ,

            updated_by_user_id UUID
                REFERENCES auth.users(id)
        );


        -- =====================================================
        -- CHILD MEDICAL REVIEWS
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_medical_reviews (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            reviewed_by_user_id UUID NOT NULL
                REFERENCES auth.users(id),

            note TEXT,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );


        -- =====================================================
        -- CHILD NOTES
        -- =====================================================

        CREATE TABLE IF NOT EXISTS public.child_notes (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

            child_id UUID NOT NULL
                REFERENCES public.child_profile(id)
                ON DELETE CASCADE,

            note TEXT NOT NULL,

            created_by_user_id UUID NOT NULL
                REFERENCES auth.users(id),

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

            consent_confirmed BOOLEAN,

            identity_verified_at TIMESTAMPTZ,

            identity_verified_by_user_id UUID
                REFERENCES auth.users(id),

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

            CONSTRAINT uq_authorized_pickup_person
                UNIQUE (
                    child_id,
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

            document_type child_document_type_enum NOT NULL,

            filename VARCHAR(255) NOT NULL,

            storage_bucket VARCHAR(255) NOT NULL,
            storage_object_key TEXT NOT NULL,

            content_type VARCHAR(100),
            size_bytes INTEGER,

            upload_status child_document_upload_status_enum
                NOT NULL DEFAULT 'pending',

            is_active BOOLEAN NOT NULL DEFAULT TRUE,

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """))