-- Shared building blocks used by the later schema files.

CREATE EXTENSION IF NOT EXISTS pgcrypto;
-- For exclusion constraints mixing = and <> (ex_authorized_pickup_persons_tenant_phone).
CREATE EXTENSION IF NOT EXISTS btree_gist;

CREATE SCHEMA tenancy;
CREATE SCHEMA auth;
-- Platform-owner reports across tenants. The app's runtime role has no
-- access (views here bypass RLS); read with an owner connection.
CREATE SCHEMA reporting;

-- Where a request comes from (docs/portals.md, section 3): 'web' (a normal
-- login) or 'kiosk' (the location's staff kiosk, with a staff member's PIN
-- for that request). Permissions are granted per channel.
CREATE TYPE auth.permission_channel_enum AS ENUM (
    'web',
    'kiosk'
);

-- What a permission is for (docs/tenant-administration.md): 'location'
-- permissions are granted to roles at a location; 'tenant' permissions
-- (the whole business: its settings, locations, Stripe, domains) are
-- granted directly to the tenant's owner.
CREATE TYPE auth.permission_scope_enum AS ENUM (
    'location',
    'tenant'
);


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

-- A location has at most one active kiosk of each kind: the family kiosk
-- (pickup people sign their children in and out) and the staff kiosk
-- (staff correct attendance, check ID, start and end shifts).
CREATE TYPE public.kiosk_kind_enum AS ENUM (
    'family',
    'staff'
);

-- Where a document's file is stored (app/integrations/storage).
CREATE TYPE public.storage_provider_enum AS ENUM (
    'gcs',
    's3'
);

-- The emails the platform sends: a fixed catalogue
-- (app/integrations/email/catalogue.py, docs/email-policy.md section 3).
CREATE TYPE public.email_type_enum AS ENUM (
    'password_reset',
    'password_changed',
    'welcome',
    'booking_confirmation',
    'refund_confirmation',
    'documents_requested',
    'child_approved',
    'kiosk_pin',
    'staff_invite',
    'new_message'
);

-- queued: logged, not yet handed to the provider. sent: accepted by the
-- provider. failed: the provider refused it, or we couldn't reach it.
-- delivered / bounced / complained: reported back by SES afterwards.
CREATE TYPE public.email_status_enum AS ENUM (
    'queued',
    'sent',
    'failed',
    'delivered',
    'bounced',
    'complained'
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

-- A Stripe refund of one booking. Stripe's requires_action stays PENDING;
-- its canceled counts as FAILED.
CREATE TYPE public.refund_status_enum AS ENUM (
    'PENDING',
    'SUCCEEDED',
    'FAILED'
);

CREATE TYPE public.pickup_relation_enum AS ENUM (
    'account_holder',
    'parent_guardian',
    'grandparent',
    'aunt_uncle',
    'family_friend',
    'neighbour',
    'nanny_babysitter',
    'other'
);

-- How a family's emergency contact is related to them (customer_profile).
-- Separate from pickup relations: an emergency contact isn't a pickup person.
CREATE TYPE public.emergency_relation_enum AS ENUM (
    'parent_guardian',
    'grandparent',
    'aunt_uncle',
    'family_friend',
    'neighbour',
    'nanny_babysitter',
    'other'
);

CREATE TYPE public.booking_status_enum AS ENUM (
    'PENDING',
    'CONFIRMED',
    'CANCELLED',
    'EXPIRED'
);
