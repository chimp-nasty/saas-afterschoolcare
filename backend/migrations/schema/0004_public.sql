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

    -- Starting session times for a new location's service; each location
    -- then sets its own (location_service_config).
    default_start_time TIME NOT NULL,
    default_end_time TIME NOT NULL,

    CONSTRAINT uq_service_types_code
        UNIQUE (code),

    CONSTRAINT ck_service_types_default_times
        CHECK (default_end_time > default_start_time)
);


-- =====================================================
-- LOCATION SERVICES
-- =====================================================

-- One row per service type per location, created with the location
-- (trg_locations_create_services) and never edited: what a location offers
-- and charges lives in location_service_config.
CREATE TABLE public.location_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,
    service_type_id SMALLINT NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_location_services_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id),

    CONSTRAINT fk_location_services_service_type
        FOREIGN KEY (service_type_id)
        REFERENCES public.service_types (id),

    CONSTRAINT uq_location_services_location_service_type
        UNIQUE (location_id, service_type_id),

    -- Target for location_service_days' and location_service_config's
    -- composite foreign keys.
    CONSTRAINT uq_location_services_id_location
        UNIQUE (id, location_id)
);


-- =====================================================
-- LOCATION SERVICE CONFIG
-- =====================================================

-- What an admin sets for one of their location's services (one row each,
-- created with the service from its type's defaults). Anyone can read it:
-- families see times, prices and policies before logging in. Only admins
-- change it.
--
-- A new location's services start inactive (not offered) until an admin
-- prices them. Prices live only here: checkout and invoices send amounts
-- to Stripe directly, so there's no Stripe catalogue to keep in step.
CREATE TABLE public.location_service_config (
    location_service_id UUID PRIMARY KEY,
    location_id UUID NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT FALSE,

    current_price_cents INTEGER NOT NULL DEFAULT 0,
    currency public.currency_code_enum NOT NULL DEFAULT 'AUD',

    -- Session times, in the location's timezone.
    start_time TIME NOT NULL,
    end_time TIME NOT NULL,

    description TEXT,

    -- A session can be refunded by the family until the end of the day this
    -- many days before it, in the location's timezone: with 2, a session on
    -- the 21st is refundable until 11:59pm on the 19th.
    refund_cutoff_days SMALLINT NOT NULL DEFAULT 2,

    -- Children this service takes, by age in whole years on the day of the
    -- session (inclusive). Checked when a child is added (against the
    -- location's widest range) and on every booking (schema/0009).
    min_child_age SMALLINT NOT NULL DEFAULT 8,
    max_child_age SMALLINT NOT NULL DEFAULT 17,

    -- A flat fee for collection after end_time plus the grace period; 0 means
    -- no late fee. Shown to families; charging it isn't built yet.
    late_fee_cents INTEGER NOT NULL DEFAULT 0,
    late_fee_grace_minutes SMALLINT NOT NULL DEFAULT 0,

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_user_id UUID,

    CONSTRAINT fk_location_service_config_service
        FOREIGN KEY (location_service_id, location_id)
        REFERENCES public.location_services (id, location_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_location_service_config_updated_by
        FOREIGN KEY (updated_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT ck_location_service_config_price_non_negative
        CHECK (current_price_cents >= 0),

    -- Nothing is bookable for free by accident.
    CONSTRAINT ck_location_service_config_active_priced
        CHECK (NOT is_active OR current_price_cents > 0),

    CONSTRAINT ck_location_service_config_times
        CHECK (end_time > start_time),

    CONSTRAINT ck_location_service_config_refund_cutoff_non_negative
        CHECK (refund_cutoff_days >= 0),

    CONSTRAINT ck_location_service_config_child_age_range
        CHECK (min_child_age >= 0 AND max_child_age >= min_child_age),

    CONSTRAINT ck_location_service_config_late_fee_non_negative
        CHECK (late_fee_cents >= 0 AND late_fee_grace_minutes >= 0)
);

CREATE TRIGGER trg_location_service_config_updated_at
    BEFORE UPDATE ON public.location_service_config
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- A new location gets every service type, each with its config.
-- SECURITY DEFINER: writes past the read-only RLS on these tables.
CREATE FUNCTION public.create_location_services()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    INSERT INTO public.location_services (location_id, service_type_id)
    SELECT NEW.id, st.id
    FROM public.service_types st;

    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_locations_create_services
    AFTER INSERT ON tenancy.locations
    FOR EACH ROW EXECUTE FUNCTION public.create_location_services();

CREATE FUNCTION public.create_location_service_config()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    INSERT INTO public.location_service_config (
        location_service_id, location_id, start_time, end_time
    )
    SELECT NEW.id, NEW.location_id, st.default_start_time, st.default_end_time
    FROM public.service_types st
    WHERE st.id = NEW.service_type_id;

    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_location_services_create_config
    AFTER INSERT ON public.location_services
    FOR EACH ROW EXECUTE FUNCTION public.create_location_service_config();


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

    -- The account holder agreed that everyone already on their pickup list
    -- may collect this child. Required when adding a child to a family
    -- with pickup people besides the account holder
    -- (trg_child_profile_pickup_consent).
    pickup_consent_confirmed_at TIMESTAMPTZ,

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

-- A child's medical review follows their medical details, so it can't be
-- skipped or set by the family (who can only read child_medical_state,
-- schema/0005):
--
--   * a new child gets a review state: pending if any medical, allergy or
--     medication details were given, otherwise not_required
--   * any change to those details (adding, editing or clearing them) sends
--     the child back to pending for staff to review again
--
-- Blank text counts as no details. Existing bookings are kept; the booking
-- rules (schema/0009) only stop new ones until staff approve.
--
-- SECURITY DEFINER: writes child_medical_state past its staff-only write
-- policy.
CREATE FUNCTION public.sync_child_medical_review()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO public.child_medical_state (child_id, review_status)
        VALUES (
            NEW.id,
            CASE
                WHEN NULLIF(btrim(NEW.medical_info), '') IS NOT NULL
                  OR NULLIF(btrim(NEW.allergy_info), '') IS NOT NULL
                  OR NULLIF(btrim(NEW.medication_info), '') IS NOT NULL
                    THEN 'pending'::public.medical_review_status_enum
                ELSE 'not_required'::public.medical_review_status_enum
            END
        );

    ELSIF NULLIF(btrim(OLD.medical_info), '') IS DISTINCT FROM NULLIF(btrim(NEW.medical_info), '')
       OR NULLIF(btrim(OLD.allergy_info), '') IS DISTINCT FROM NULLIF(btrim(NEW.allergy_info), '')
       OR NULLIF(btrim(OLD.medication_info), '') IS DISTINCT FROM NULLIF(btrim(NEW.medication_info), '')
    THEN
        -- Not reviewed by anyone yet, so no reviewer.
        UPDATE public.child_medical_state
        SET review_status = 'pending',
            updated_by_user_id = NULL
        WHERE child_id = NEW.id;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_child_profile_medical_review
    AFTER INSERT OR UPDATE OF medical_info, allergy_info, medication_info
    ON public.child_profile
    FOR EACH ROW EXECUTE FUNCTION public.sync_child_medical_review();


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

-- Who may collect a family's children at a location: the account holder
-- plus up to three people the family adds. Everyone on the list may collect
-- every child on the account. Each person is also a kiosk login (phone and
-- 4-digit PIN) for signing children in and out on a registered device.
--
--   * one phone number belongs to one family across the whole tenant (the
--     same family may be listed at several of its locations)
--   * the account holder's row is kept in sync with their name and profile
--     phone (sync_account_holder_pickups); families can't edit or remove it
--   * only staff set the ID check and kiosk fields
--     (trg_authorized_pickup_persons_rules)
--   * changing a name or phone resets the ID check; changing the phone also
--     resets the kiosk PIN (it's a new login)
--
-- Kiosk PIN: pin_hash NULL means the default PIN 1111, which must be
-- changed at the next kiosk login. Five wrong PINs lock the person
-- (pin_locked_at), not the device, until staff reset it. A staff reset sets
-- kiosk_pin_reset_at: if the default PIN isn't changed within 30 minutes of
-- it, it stops working and staff must reset it again.
CREATE TABLE public.authorized_pickup_persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,
    -- Set from the location by trg_authorized_pickup_persons_rules, for the
    -- tenant-wide phone rule.
    tenant_id UUID NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    -- Digits only, so formatting can't get around the phone rules.
    phone VARCHAR(15) NOT NULL,

    relation public.pickup_relation_enum NOT NULL,
    relation_other VARCHAR(100),

    -- The account holder's declarations when adding the person.
    consent_confirmed_at TIMESTAMPTZ,
    adult_confirmed_at TIMESTAMPTZ,

    identity_verified_at TIMESTAMPTZ,
    identity_verified_by_user_id UUID,

    pin_hash TEXT,
    failed_pin_attempts SMALLINT NOT NULL DEFAULT 0,
    pin_locked_at TIMESTAMPTZ,
    kiosk_pin_reset_at TIMESTAMPTZ,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_authorized_pickup_persons_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_authorized_pickup_persons_location
        FOREIGN KEY (location_id, tenant_id)
        REFERENCES tenancy.locations (id, tenant_id),

    CONSTRAINT fk_authorized_pickup_persons_verified_by
        FOREIGN KEY (identity_verified_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT ck_authorized_pickup_persons_phone_format
        CHECK (phone ~ '^[0-9]{8,15}$'),

    -- "Other" needs its own wording; every other relation has none.
    CONSTRAINT ck_authorized_pickup_persons_relation_other
        CHECK (
            (relation = 'other')
            = (relation_other IS NOT NULL AND btrim(relation_other) <> '')
        ),

    CONSTRAINT ck_authorized_pickup_persons_declarations
        CHECK (
            relation = 'account_holder'
            OR (consent_confirmed_at IS NOT NULL AND adult_confirmed_at IS NOT NULL)
        ),

    CONSTRAINT ck_authorized_pickup_persons_failed_pin_attempts
        CHECK (failed_pin_attempts >= 0),

    -- A phone number may appear on several active rows in a tenant only if
    -- they're the same family's (one per location).
    CONSTRAINT ex_authorized_pickup_persons_tenant_phone
        EXCLUDE USING gist (
            tenant_id WITH =,
            phone WITH =,
            user_id WITH <>
        )
        WHERE (is_active)
);

-- A family lists a phone number once.
CREATE UNIQUE INDEX uq_authorized_pickup_persons_family_phone
    ON public.authorized_pickup_persons (user_id, location_id, phone)
    WHERE is_active;

-- One account holder row per family per location.
CREATE UNIQUE INDEX uq_authorized_pickup_persons_account_holder
    ON public.authorized_pickup_persons (user_id, location_id)
    WHERE is_active AND relation = 'account_holder';

CREATE TRIGGER trg_authorized_pickup_persons_updated_at
    BEFORE UPDATE ON public.authorized_pickup_persons
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- The rules every write to a pickup row goes through. SECURITY DEFINER:
-- counts the family's rows and checks the writer's role past RLS.
--
-- The staff-only fields are protected for writes made as a logged-in user
-- (app.user_id set, as every RLS request is). Writes with no user session
-- are trusted server code: migrations, maintenance, and the kiosk endpoints
-- still to be built (which change PIN fields without a staff login).
CREATE FUNCTION public.enforce_pickup_person_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_others INTEGER;
BEGIN
    SELECT l.tenant_id
    INTO NEW.tenant_id
    FROM tenancy.locations l
    WHERE l.id = NEW.location_id;

    NEW.phone := regexp_replace(NEW.phone, '\D', '', 'g');

    -- ID check and kiosk fields: staff only. A family's write can't set
    -- them on a new row or change them on an existing one.
    IF auth.current_user_id() IS NOT NULL
       AND NOT auth.is_location_staff(NEW.location_id) THEN
        IF TG_OP = 'INSERT' THEN
            NEW.identity_verified_at := NULL;
            NEW.identity_verified_by_user_id := NULL;
            NEW.pin_hash := NULL;
            NEW.failed_pin_attempts := 0;
            NEW.pin_locked_at := NULL;
            NEW.kiosk_pin_reset_at := NULL;
        ELSE
            NEW.identity_verified_at := OLD.identity_verified_at;
            NEW.identity_verified_by_user_id := OLD.identity_verified_by_user_id;
            NEW.pin_hash := OLD.pin_hash;
            NEW.failed_pin_attempts := OLD.failed_pin_attempts;
            NEW.pin_locked_at := OLD.pin_locked_at;
            NEW.kiosk_pin_reset_at := OLD.kiosk_pin_reset_at;
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- A different name or phone is a different person to check.
        IF NEW.first_name IS DISTINCT FROM OLD.first_name
           OR NEW.last_name IS DISTINCT FROM OLD.last_name
           OR NEW.phone IS DISTINCT FROM OLD.phone THEN
            NEW.identity_verified_at := NULL;
            NEW.identity_verified_by_user_id := NULL;
        END IF;

        -- A new phone is a new kiosk login: back to the default PIN.
        IF NEW.phone IS DISTINCT FROM OLD.phone THEN
            NEW.pin_hash := NULL;
            NEW.failed_pin_attempts := 0;
            NEW.pin_locked_at := NULL;
            NEW.kiosk_pin_reset_at := NULL;
        END IF;
    END IF;

    -- At most three people besides the account holder. The lock makes two
    -- adds for the same family queue, so they can't both take the last place.
    IF NEW.is_active
       AND NEW.relation <> 'account_holder'
       AND (TG_OP = 'INSERT' OR NOT OLD.is_active) THEN
        PERFORM pg_advisory_xact_lock(
            hashtextextended(NEW.user_id::text || NEW.location_id::text, 0)
        );

        SELECT count(*)
        INTO v_others
        FROM public.authorized_pickup_persons p
        WHERE p.user_id = NEW.user_id
          AND p.location_id = NEW.location_id
          AND p.is_active
          AND p.relation <> 'account_holder'
          AND p.id <> NEW.id;

        IF v_others >= 3 THEN
            RAISE EXCEPTION 'Family % already has 3 pickup people', NEW.user_id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_authorized_pickup_persons_limit',
                      TABLE = 'authorized_pickup_persons',
                      SCHEMA = 'public';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_authorized_pickup_persons_rules
    BEFORE INSERT OR UPDATE ON public.authorized_pickup_persons
    FOR EACH ROW EXECUTE FUNCTION public.enforce_pickup_person_rules();

-- Keep a user's account holder rows (one per location where they're a
-- customer) matching their name and profile phone. Creates them once the
-- profile has a phone. A cleared phone leaves the rows as they are.
-- SECURITY DEFINER: writes the rows past RLS for the trigger callers below.
CREATE FUNCTION public.sync_account_holder_pickups(p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_phone TEXT;
    v_first_name VARCHAR(100);
    v_last_name VARCHAR(100);
    v_location_id UUID;
BEGIN
    SELECT NULLIF(regexp_replace(cp.phone, '\D', '', 'g'), '')
    INTO v_phone
    FROM public.customer_profile cp
    WHERE cp.user_id = p_user_id;

    IF v_phone IS NULL THEN
        RETURN;
    END IF;

    SELECT u.first_name, u.last_name
    INTO v_first_name, v_last_name
    FROM auth.users u
    WHERE u.id = p_user_id;

    FOR v_location_id IN
        SELECT lur.location_id
        FROM auth.location_user_roles lur
        JOIN auth.roles r
            ON r.id = lur.role_id
        WHERE lur.user_id = p_user_id
          AND r.code = 'customer'
    LOOP
        UPDATE public.authorized_pickup_persons
        SET first_name = v_first_name,
            last_name = v_last_name,
            phone = v_phone
        WHERE user_id = p_user_id
          AND location_id = v_location_id
          AND relation = 'account_holder'
          AND is_active
          AND (first_name, last_name, phone)
              IS DISTINCT FROM (v_first_name, v_last_name, v_phone);

        INSERT INTO public.authorized_pickup_persons (
            user_id, location_id, first_name, last_name, phone, relation
        )
        SELECT p_user_id, v_location_id, v_first_name, v_last_name, v_phone, 'account_holder'
        WHERE NOT EXISTS (
            SELECT 1
            FROM public.authorized_pickup_persons p
            WHERE p.user_id = p_user_id
              AND p.location_id = v_location_id
              AND p.relation = 'account_holder'
              AND p.is_active
        );
    END LOOP;
END;
$$;

-- Callers: a profile phone change, a name change, or becoming a customer
-- at another location.
CREATE FUNCTION public.trg_sync_account_holder_pickups()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_TABLE_NAME = 'users' THEN
        PERFORM public.sync_account_holder_pickups(NEW.id);
    ELSE
        PERFORM public.sync_account_holder_pickups(NEW.user_id);
    END IF;

    RETURN NULL;
END;
$$;

CREATE TRIGGER trg_customer_profile_account_holder_pickup
    AFTER INSERT OR UPDATE OF phone ON public.customer_profile
    FOR EACH ROW EXECUTE FUNCTION public.trg_sync_account_holder_pickups();

CREATE TRIGGER trg_users_account_holder_pickup
    AFTER UPDATE OF first_name, last_name ON auth.users
    FOR EACH ROW EXECUTE FUNCTION public.trg_sync_account_holder_pickups();

CREATE TRIGGER trg_location_user_roles_account_holder_pickup
    AFTER INSERT ON auth.location_user_roles
    FOR EACH ROW EXECUTE FUNCTION public.trg_sync_account_holder_pickups();

-- Adding a child extends the family's pickup list to them, so the account
-- holder must agree when there's anyone on it besides themselves.
-- SECURITY DEFINER: reads the family's pickup rows past RLS.
CREATE FUNCTION public.enforce_child_pickup_consent()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NEW.pickup_consent_confirmed_at IS NULL
       AND EXISTS (
           SELECT 1
           FROM public.authorized_pickup_persons p
           WHERE p.user_id = NEW.user_id
             AND p.location_id = NEW.location_id
             AND p.is_active
             AND p.relation <> 'account_holder'
       ) THEN
        RAISE EXCEPTION 'Child needs consent for the existing pickup list'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_profile_pickup_consent',
                  TABLE = 'child_profile',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_child_profile_pickup_consent
    BEFORE INSERT ON public.child_profile
    FOR EACH ROW EXECUTE FUNCTION public.enforce_child_pickup_consent();


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

    -- When the checkout was opened, which can be well before it was paid.
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- Set by the webhook when the attempt moves to SUCCEEDED.
    paid_at TIMESTAMPTZ,

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

-- A refund of one booking (one child on one day), back to the payment it
-- was paid with. Refunds go to Stripe first; the webhook settles them: on
-- success the booking becomes CANCELLED / REFUNDED and its place is
-- released. Until then the place stays held.
--
-- Who can refund, and until when (public.booking_is_refundable):
--   * the family: until refund_cutoff_days before the session
--   * staff and above: until the end of the session day
-- A booking has at most one active refund (pending or succeeded); a failed
-- one can be tried again.
CREATE TABLE public.refunds (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    booking_id UUID NOT NULL,
    location_id UUID NOT NULL,
    user_id UUID NOT NULL,
    requested_by_user_id UUID NOT NULL,

    -- Set from the booking by trg_refunds_rules: its group's successful
    -- payment, and its price.
    payment_attempt_id UUID NOT NULL,
    amount_cents INTEGER NOT NULL,
    currency public.currency_code_enum NOT NULL,

    status public.refund_status_enum NOT NULL DEFAULT 'PENDING',

    reason TEXT,
    stripe_refund_id VARCHAR(255),
    failed_at TIMESTAMPTZ,
    failure_reason TEXT,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    processed_at TIMESTAMPTZ,

    CONSTRAINT fk_refunds_booking
        FOREIGN KEY (booking_id, user_id, location_id)
        REFERENCES public.bookings (id, user_id, location_id),

    CONSTRAINT fk_refunds_payment_attempt
        FOREIGN KEY (payment_attempt_id)
        REFERENCES public.payment_attempts (id),

    CONSTRAINT fk_refunds_requested_by
        FOREIGN KEY (requested_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT uq_refunds_stripe_refund
        UNIQUE (stripe_refund_id),

    CONSTRAINT ck_refunds_amount_positive
        CHECK (amount_cents > 0)
);

CREATE UNIQUE INDEX uq_refunds_active_booking
    ON public.refunds (booking_id)
    WHERE status IN ('PENDING', 'SUCCEEDED');

-- Whether a booking can be refunded now: confirmed and paid, inside the
-- window (by_staff: until the end of the session day; otherwise until
-- refund_cutoff_days before it, location time), and no active refund.
-- plpgsql so it can use effective_booking_status (schema/0009) at run time.
CREATE FUNCTION public.booking_is_refundable(
    p_booking_id UUID,
    p_by_staff BOOLEAN
)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN EXISTS (
        SELECT 1
        FROM public.bookings b
        JOIN public.location_service_days d
            ON d.id = b.location_service_day_id
        JOIN public.location_service_config lsc
            ON lsc.location_service_id = d.location_service_id
        JOIN tenancy.locations l
            ON l.id = b.location_id
        WHERE b.id = p_booking_id
          AND public.effective_booking_status(b.booking_status, b.created_at) = 'CONFIRMED'
          AND b.payment_status = 'PAID'
          AND (now() AT TIME ZONE l.timezone)::date <= CASE
                  WHEN p_by_staff THEN d.service_date
                  ELSE d.service_date - lsc.refund_cutoff_days
              END
          AND NOT EXISTS (
              SELECT 1
              FROM public.refunds r
              WHERE r.booking_id = b.id
                AND r.status IN ('PENDING', 'SUCCEEDED')
          )
    );
END;
$$;

-- A new refund must be for a refundable booking (by the requester's role),
-- and takes its amount, currency and payment from the booking.
CREATE FUNCTION public.enforce_refund_rules()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    -- Checked first so it reads as "already requested", not "can't be
    -- refunded" (booking_is_refundable is false while one is pending too).
    -- uq_refunds_active_booking still catches two requests at once.
    IF EXISTS (
        SELECT 1
        FROM public.refunds r
        WHERE r.booking_id = NEW.booking_id
          AND r.status IN ('PENDING', 'SUCCEEDED')
    ) THEN
        RAISE EXCEPTION 'Booking % already has a refund', NEW.booking_id
            USING ERRCODE = 'unique_violation',
                  CONSTRAINT = 'uq_refunds_active_booking',
                  TABLE = 'refunds',
                  SCHEMA = 'public';
    END IF;

    IF NOT public.booking_is_refundable(
        NEW.booking_id,
        COALESCE(auth.is_location_staff(NEW.location_id), FALSE)
    ) THEN
        RAISE EXCEPTION 'Booking % can''t be refunded', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_refunds_booking_refundable',
                  TABLE = 'refunds',
                  SCHEMA = 'public';
    END IF;

    SELECT b.price_snapshot_cents, b.currency, pa.id
    INTO NEW.amount_cents, NEW.currency, NEW.payment_attempt_id
    FROM public.bookings b
    JOIN public.payment_attempts pa
        ON pa.booking_group_id = b.booking_group_id
       AND pa.stripe_status = 'SUCCEEDED'
       AND pa.stripe_payment_intent_id IS NOT NULL
    WHERE b.id = NEW.booking_id;

    -- Paid, but with nothing in Stripe to refund against.
    IF NEW.payment_attempt_id IS NULL THEN
        RAISE EXCEPTION 'Booking % has no refundable payment', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_refunds_booking_refundable',
                  TABLE = 'refunds',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_refunds_rules
    BEFORE INSERT ON public.refunds
    FOR EACH ROW EXECUTE FUNCTION public.enforce_refund_rules();


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
