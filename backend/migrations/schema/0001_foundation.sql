-- Shared building blocks used by the later schema files.

CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE SCHEMA tenancy;
CREATE SCHEMA auth;


-- =====================================================
-- updated_at
-- =====================================================
-- Attached to every table with an updated_at column, so the column
-- changes on every UPDATE without the app having to set it.

CREATE FUNCTION public.set_updated_at()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$;


-- =====================================================
-- ENUMS
-- =====================================================

CREATE TYPE public.currency_code_enum AS ENUM (
    'AUD',
    'NZD',
    'USD'
);

CREATE TYPE public.medical_review_status_enum AS ENUM (
    'not_required',
    'pending',
    'documentation_requested',
    'approved'
);

CREATE TYPE public.child_document_type_enum AS ENUM (
    'medical_action_plan',
    'asthma_action_plan',
    'allergy_anaphylaxis_plan',
    'other'
);

CREATE TYPE public.child_document_upload_status_enum AS ENUM (
    'pending',
    'uploaded',
    'failed'
);

CREATE TYPE public.stripe_status_enum AS ENUM (
    'PENDING',
    'SUCCEEDED',
    'FAILED'
);

CREATE TYPE public.payment_status_enum AS ENUM (
    'PENDING',
    'PAID',
    'REFUNDED',
    'FAILED'
);

CREATE TYPE public.booking_status_enum AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED',
    'EXPIRED'
);
