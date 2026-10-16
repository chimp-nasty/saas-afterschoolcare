-- Composite foreign keys (child, user, location) keep rows consistent
-- with each other. RLS does not apply to foreign key checks, so these
-- are what stop e.g. a booking referencing another family's child.


-- =====================================================
-- SERVICE TYPES
-- =====================================================

CREATE TABLE public.service_types (
    id SMALLSERIAL PRIMARY KEY,

    code VARCHAR(32) NOT NULL,
    name VARCHAR(64) NOT NULL,

    CONSTRAINT uq_service_types_code
        UNIQUE (code)
);


-- =====================================================
-- LOCATION SERVICES
-- =====================================================

CREATE TABLE public.location_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,
    service_type_id SMALLINT NOT NULL,

    stripe_product_id VARCHAR(255),
    current_price_cents INTEGER NOT NULL,
    currency public.currency_code_enum NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_location_services_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id),

    CONSTRAINT fk_location_services_service_type
        FOREIGN KEY (service_type_id)
        REFERENCES public.service_types (id),

    CONSTRAINT uq_location_services_location_service_type
        UNIQUE (location_id, service_type_id),

    CONSTRAINT uq_location_services_stripe_product
        UNIQUE (stripe_product_id),

    -- Target for location_service_days' composite foreign key.
    CONSTRAINT uq_location_services_id_location
        UNIQUE (id, location_id),

    CONSTRAINT ck_location_services_price_non_negative
        CHECK (current_price_cents >= 0)
);

CREATE TRIGGER trg_location_services_updated_at
    BEFORE UPDATE ON public.location_services
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- LOCATION SERVICE DAYS
-- =====================================================

CREATE TABLE public.location_service_days (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_service_id UUID NOT NULL,
    location_id UUID NOT NULL,

    service_date DATE NOT NULL,
    is_open BOOLEAN NOT NULL DEFAULT TRUE,
    capacity INTEGER NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- The day's location must be its service's location.
    CONSTRAINT fk_location_service_days_location_service
        FOREIGN KEY (location_service_id, location_id)
        REFERENCES public.location_services (id, location_id),

    CONSTRAINT uq_location_service_days_service_date
        UNIQUE (location_service_id, service_date),

    -- Target for bookings' composite foreign key.
    CONSTRAINT uq_location_service_days_id_location
        UNIQUE (id, location_id),

    CONSTRAINT ck_location_service_days_capacity_non_negative
        CHECK (capacity >= 0)
);


-- =====================================================
-- CUSTOMER PROFILE
-- =====================================================

CREATE TABLE public.customer_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    phone VARCHAR(30),
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    suburb VARCHAR(100),
    state VARCHAR(100),
    postcode VARCHAR(20),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_customer_profile_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_customer_profile_user
        UNIQUE (user_id),

    CONSTRAINT ck_customer_profile_state
        CHECK (
            state IN ('NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT')
        )
);

CREATE TRIGGER trg_customer_profile_updated_at
    BEFORE UPDATE ON public.customer_profile
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- CUSTOMER KIOSK PINS
-- =====================================================

CREATE TABLE public.customer_kiosk_pins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    pin_hash TEXT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_used_at TIMESTAMPTZ,

    CONSTRAINT fk_customer_kiosk_pins_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_customer_kiosk_pins_user
        UNIQUE (user_id)
);

CREATE TRIGGER trg_customer_kiosk_pins_updated_at
    BEFORE UPDATE ON public.customer_kiosk_pins
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- CHILD PROFILE
-- =====================================================

CREATE TABLE public.child_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,
    user_id UUID NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    dob DATE NOT NULL,

    medical_info TEXT,
    allergy_info TEXT,
    medication_info TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_child_profile_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id),

    CONSTRAINT fk_child_profile_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    -- Target for the composite foreign keys from bookings and actions.
    CONSTRAINT uq_child_profile_id_user_location
        UNIQUE (id, user_id, location_id)
);

-- One active child per family per location with the same name and date
-- of birth (case-insensitive). Deactivated duplicates are allowed.
CREATE UNIQUE INDEX uq_child_profile_active_identity
    ON public.child_profile (
        user_id,
        location_id,
        lower(first_name),
        lower(last_name),
        dob
    )
    WHERE is_active;

CREATE TRIGGER trg_child_profile_updated_at
    BEFORE UPDATE ON public.child_profile
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- CHILD MEDICAL STATE
-- =====================================================

CREATE TABLE public.child_medical_state (
    child_id UUID PRIMARY KEY,

    review_status public.medical_review_status_enum
        NOT NULL DEFAULT 'not_required',

    updated_at TIMESTAMPTZ,
    updated_by_user_id UUID,

    CONSTRAINT fk_child_medical_state_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_child_medical_state_updated_by
        FOREIGN KEY (updated_by_user_id)
        REFERENCES auth.users (id)
);

CREATE TRIGGER trg_child_medical_state_updated_at
    BEFORE UPDATE ON public.child_medical_state
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- CHILD NOTES
-- =====================================================

CREATE TABLE public.child_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    child_id UUID NOT NULL,

    note TEXT NOT NULL,

    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_child_notes_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_child_notes_created_by
        FOREIGN KEY (created_by_user_id)
        REFERENCES auth.users (id)
);


-- =====================================================
-- AUTHORIZED PICKUP PERSONS
-- =====================================================

CREATE TABLE public.authorized_pickup_persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    child_id UUID NOT NULL,
    user_id UUID NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    phone VARCHAR(30) NOT NULL,
    relation VARCHAR(100) NOT NULL,

    consent_confirmed BOOLEAN,
    identity_verified_at TIMESTAMPTZ,
    identity_verified_by_user_id UUID,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_authorized_pickup_persons_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_authorized_pickup_persons_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id),

    CONSTRAINT fk_authorized_pickup_persons_verified_by
        FOREIGN KEY (identity_verified_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT uq_authorized_pickup_persons_child_phone
        UNIQUE (child_id, phone)
);

CREATE TRIGGER trg_authorized_pickup_persons_updated_at
    BEFORE UPDATE ON public.authorized_pickup_persons
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- CHILD DOCUMENTS
-- =====================================================

CREATE TABLE public.child_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    child_id UUID NOT NULL,
    uploaded_by_user_id UUID NOT NULL,

    document_type public.child_document_type_enum NOT NULL,
    filename VARCHAR(255) NOT NULL,
    storage_bucket VARCHAR(255) NOT NULL,
    storage_object_key TEXT NOT NULL,
    content_type VARCHAR(100),
    size_bytes INTEGER,

    upload_status public.child_document_upload_status_enum
        NOT NULL DEFAULT 'pending',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_child_documents_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_child_documents_uploaded_by
        FOREIGN KEY (uploaded_by_user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE
);

CREATE TRIGGER trg_child_documents_updated_at
    BEFORE UPDATE ON public.child_documents
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- LOCATION KIOSK DEVICES
-- =====================================================

CREATE TABLE public.location_kiosk_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,

    name TEXT NOT NULL,
    setup_secret_hash TEXT,
    token_version INTEGER NOT NULL DEFAULT 1,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paired_at TIMESTAMPTZ,
    last_used TIMESTAMPTZ,

    CONSTRAINT fk_location_kiosk_devices_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
);


-- =====================================================
-- BOOKING GROUPS
-- =====================================================

CREATE TABLE public.booking_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    idempotency_key VARCHAR(128) NOT NULL,

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,

    source VARCHAR(32),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_booking_groups_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id),

    CONSTRAINT fk_booking_groups_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id),

    CONSTRAINT uq_booking_groups_user_idempotency
        UNIQUE (user_id, idempotency_key),

    -- Target for the composite foreign keys from bookings and payment_attempts.
    CONSTRAINT uq_booking_groups_id_user_location
        UNIQUE (id, user_id, location_id)
);


-- =====================================================
-- BOOKINGS
-- =====================================================

CREATE TABLE public.bookings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,
    user_id UUID NOT NULL,
    booking_group_id UUID NOT NULL,
    location_service_day_id UUID NOT NULL,
    child_id UUID NOT NULL,

    booking_status public.booking_status_enum
        NOT NULL DEFAULT 'PENDING',

    payment_status public.payment_status_enum
        NOT NULL DEFAULT 'PENDING',

    cancelled_at TIMESTAMPTZ,

    price_snapshot_cents INTEGER NOT NULL,
    currency public.currency_code_enum NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_bookings_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id),

    CONSTRAINT fk_bookings_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id),

    -- The child belongs to this booking's user, at this location.
    CONSTRAINT fk_bookings_child
        FOREIGN KEY (child_id, user_id, location_id)
        REFERENCES public.child_profile (id, user_id, location_id),

    -- The service day is at this booking's location.
    CONSTRAINT fk_bookings_location_service_day
        FOREIGN KEY (location_service_day_id, location_id)
        REFERENCES public.location_service_days (id, location_id),

    -- The group belongs to this booking's user, at this location.
    CONSTRAINT fk_bookings_booking_group
        FOREIGN KEY (booking_group_id, user_id, location_id)
        REFERENCES public.booking_groups (id, user_id, location_id),

    -- Target for refunds' composite foreign key.
    CONSTRAINT uq_bookings_id_user_location
        UNIQUE (id, user_id, location_id),

    CONSTRAINT ck_bookings_price_non_negative
        CHECK (price_snapshot_cents >= 0)
);

-- A child can hold only one live booking per service day.
CREATE UNIQUE INDEX uq_bookings_active_child_service_day
    ON public.bookings (
        child_id,
        location_service_day_id
    )
    WHERE booking_status IN ('PENDING', 'CONFIRMED');

CREATE TRIGGER trg_bookings_updated_at
    BEFORE UPDATE ON public.bookings
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- PAYMENT ATTEMPTS
-- =====================================================

CREATE TABLE public.payment_attempts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,
    user_id UUID NOT NULL,
    booking_group_id UUID NOT NULL,

    stripe_status public.stripe_status_enum
        NOT NULL DEFAULT 'PENDING',

    stripe_payment_intent_id VARCHAR(255),
    stripe_checkout_session_id VARCHAR(255),
    stripe_receipt_url TEXT,

    total_cents INTEGER NOT NULL,
    currency public.currency_code_enum NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_payment_attempts_booking_group
        FOREIGN KEY (booking_group_id, user_id, location_id)
        REFERENCES public.booking_groups (id, user_id, location_id),

    CONSTRAINT uq_payment_attempts_stripe_payment_intent
        UNIQUE (stripe_payment_intent_id),

    CONSTRAINT uq_payment_attempts_stripe_checkout_session
        UNIQUE (stripe_checkout_session_id),

    CONSTRAINT ck_payment_attempts_total_non_negative
        CHECK (total_cents >= 0)
);


-- =====================================================
-- REFUNDS
-- =====================================================

CREATE TABLE public.refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    booking_id UUID NOT NULL,
    location_id UUID NOT NULL,
    user_id UUID NOT NULL,
    requested_by_user_id UUID NOT NULL,

    reason TEXT,
    stripe_refund_id VARCHAR(255),
    failed_at TIMESTAMPTZ,
    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,

    CONSTRAINT fk_refunds_booking
        FOREIGN KEY (booking_id, user_id, location_id)
        REFERENCES public.bookings (id, user_id, location_id),

    CONSTRAINT fk_refunds_requested_by
        FOREIGN KEY (requested_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT uq_refunds_stripe_refund
        UNIQUE (stripe_refund_id)
);


-- =====================================================
-- ATTENDANCE RECORDS
-- =====================================================

CREATE TABLE public.attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    booking_id UUID NOT NULL,

    signed_in_at TIMESTAMPTZ,
    signed_out_at TIMESTAMPTZ,
    signed_in_by_user_id UUID,
    signed_out_by_user_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_attendance_records_booking
        FOREIGN KEY (booking_id)
        REFERENCES public.bookings (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_attendance_records_signed_in_by
        FOREIGN KEY (signed_in_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT fk_attendance_records_signed_out_by
        FOREIGN KEY (signed_out_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT uq_attendance_records_booking
        UNIQUE (booking_id),

    CONSTRAINT ck_attendance_records_signout_requires_signin
        CHECK (
            signed_out_at IS NULL
            OR signed_in_at IS NOT NULL
        ),

    CONSTRAINT ck_attendance_records_signout_after_signin
        CHECK (
            signed_out_at IS NULL
            OR signed_out_at >= signed_in_at
        )
);

CREATE TRIGGER trg_attendance_records_updated_at
    BEFORE UPDATE ON public.attendance_records
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- ACTIONS
-- =====================================================

CREATE TABLE public.actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,
    child_id UUID,

    target TEXT NOT NULL,
    title TEXT NOT NULL,
    message TEXT NOT NULL,

    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    cited_at TIMESTAMPTZ,

    CONSTRAINT fk_actions_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_actions_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    -- When an action is about a child, it's that user's child at this
    -- location. Not checked when child_id is NULL.
    CONSTRAINT fk_actions_child
        FOREIGN KEY (child_id, user_id, location_id)
        REFERENCES public.child_profile (id, user_id, location_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_actions_created_by
        FOREIGN KEY (created_by_user_id)
        REFERENCES auth.users (id)
);
