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
    -- Shown instead of "Ages X–Y" (e.g. "Years 7 to 12"); the limits above
    -- still decide who can book.
    age_label VARCHAR(40),
    -- The program, as the centre's programs page describes it
    -- (docs/public-site.md, section 4), after the description. Each is
    -- optional; written by a superadmin there, inline on the page.
    inclusions VARCHAR(2000),
    drop_off_pickup VARCHAR(2000),
    what_to_bring VARCHAR(2000),
    activities VARCHAR(2000),
    -- The service the centre's page leads with (docs/public-site.md): its
    -- times, ages and next session. At most one per location
    -- (uq_location_service_config_featured); none means the first offered.
    is_featured BOOLEAN NOT NULL DEFAULT FALSE,

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

CREATE UNIQUE INDEX uq_location_service_config_featured
    ON public.location_service_config (location_id)
    WHERE is_featured;

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

    -- Why a closed day is closed (e.g. "Staff training"), for admins.
    closed_reason VARCHAR(200),

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
        CHECK (capacity >= 0),

    -- Only a closed day has a reason.
    CONSTRAINT ck_location_service_days_closed_reason
        CHECK (is_open = FALSE OR closed_reason IS NULL)
);

-- The places a service day's bookings hold: every family's live bookings
-- (pending or confirmed; a lapsed hold doesn't count), as the booking rules
-- count them. plpgsql: booking_hold_lapsed is in schema/0009.
CREATE FUNCTION public.service_day_places_held(p_location_service_day_id UUID)
RETURNS integer
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN (
        SELECT count(*)::integer
        FROM public.bookings b
        WHERE b.location_service_day_id = p_location_service_day_id
          AND b.booking_status IN ('PENDING', 'CONFIRMED')
          AND NOT public.booking_hold_lapsed(b.booking_status, b.created_at)
    );
END;
$$;

-- What the centre's page shows about a service's coming sessions before
-- login (docs/public-site.md): the date of the next open day that hasn't
-- finished (in the location's time), and the weekdays its open days fall on
-- over the next four weeks (ISO: 1 Monday to 7 Sunday). Service days are
-- only readable by the location's people (RLS), so nothing else about them
-- (capacity, closures, reasons) leaves this function.
CREATE FUNCTION public.service_upcoming_sessions(p_location_service_id UUID)
RETURNS TABLE (next_session_date DATE, weekdays SMALLINT[])
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public, tenancy
AS $$
    WITH here AS (
        SELECT (now() AT TIME ZONE l.timezone) AS local_now, c.end_time
        FROM public.location_service_config c
        JOIN tenancy.locations l ON l.id = c.location_id
        WHERE c.location_service_id = p_location_service_id
    ),
    coming AS (
        SELECT d.service_date
        FROM public.location_service_days d, here
        WHERE d.location_service_id = p_location_service_id
          AND d.is_open
          AND (
              d.service_date > here.local_now::date
              OR (d.service_date = here.local_now::date AND here.end_time > here.local_now::time)
          )
    )
    SELECT
        (SELECT min(service_date) FROM coming),
        ARRAY(
            SELECT DISTINCT extract(isodow FROM coming.service_date)::smallint
            FROM coming, here
            WHERE coming.service_date < here.local_now::date + 28
            ORDER BY 1
        );
$$;

-- Changing service days never strands a booking. From a user session:
--   * days are added for today or later (location time), never the past
--   * capacity can't go below the places its bookings hold
--   * a day with bookings holding places can't be closed (refund first)
--   * a day that has ever had a booking can't be deleted (close it instead)
-- Writes with no user session are trusted server code (seeds, tests).
CREATE FUNCTION public.enforce_service_day_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_held INTEGER;
BEGIN
    IF auth.current_user_id() IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    IF TG_OP = 'INSERT' THEN
        IF NEW.service_date < (
            SELECT (now() AT TIME ZONE l.timezone)::date
            FROM tenancy.locations l
            WHERE l.id = NEW.location_id
        ) THEN
            RAISE EXCEPTION 'Service day % is in the past', NEW.service_date
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_location_service_days_not_past',
                      TABLE = 'location_service_days',
                      SCHEMA = 'public';
        END IF;

        RETURN NEW;
    END IF;

    IF TG_OP = 'DELETE' THEN
        IF EXISTS (SELECT 1 FROM public.bookings b WHERE b.location_service_day_id = OLD.id) THEN
            RAISE EXCEPTION 'Service day % has had bookings', OLD.id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_location_service_days_delete_booked',
                      TABLE = 'location_service_days',
                      SCHEMA = 'public';
        END IF;

        RETURN OLD;
    END IF;

    v_held := public.service_day_places_held(NEW.id);

    IF NEW.capacity < OLD.capacity AND NEW.capacity < v_held THEN
        RAISE EXCEPTION 'Service day % has % places booked', NEW.id, v_held
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_service_days_capacity_held',
                  TABLE = 'location_service_days',
                  SCHEMA = 'public';
    END IF;

    IF OLD.is_open AND NOT NEW.is_open AND v_held > 0 THEN
        RAISE EXCEPTION 'Service day % has % places booked', NEW.id, v_held
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_service_days_close_booked',
                  TABLE = 'location_service_days',
                  SCHEMA = 'public';
    END IF;

    -- Reopening clears the reason.
    IF NEW.is_open THEN
        NEW.closed_reason := NULL;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_location_service_days_rules
    BEFORE INSERT OR UPDATE OR DELETE ON public.location_service_days
    FOR EACH ROW EXECUTE FUNCTION public.enforce_service_day_rules();


-- =====================================================
-- CUSTOMER PROFILE
-- =====================================================

-- The parent's contact details and their emergency contact. All of them
-- are needed before booking or adding a child (the services check the
-- missing ones; CustomerProfileRepository.get_missing_profile_fields).
--
-- Emergency contact: exactly one per family, called when the parent can't
-- be reached. Not a pickup person (no link to authorized_pickup_persons),
-- and its phone needn't be unique, only a valid Australian number that
-- isn't the parent's own. Families own it; staff read it (the admin family
-- page, the staff kiosk), never change it.
CREATE TABLE public.customer_profile (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,

    phone VARCHAR(30),
    address_line_1 VARCHAR(255),
    address_line_2 VARCHAR(255),
    suburb VARCHAR(100),
    state VARCHAR(100),
    postcode VARCHAR(20),

    emergency_contact_name VARCHAR(200),
    -- 10 digits, normalised like every phone ("0400000000").
    emergency_contact_phone VARCHAR(15),
    emergency_contact_relation public.emergency_relation_enum,
    -- Their own words, when the relation is "other".
    emergency_contact_relation_other VARCHAR(100),

    -- The business's terms the family accepted when they signed up (its
    -- current version then; tenancy.tenant_documents keeps every version).
    -- None if it had none. Never changes (trg_customer_profile_terms_fixed).
    terms_document_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_customer_profile_terms_document
        FOREIGN KEY (terms_document_id)
        REFERENCES tenancy.tenant_documents (id),

    CONSTRAINT fk_customer_profile_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_customer_profile_user
        UNIQUE (user_id),

    CONSTRAINT ck_customer_profile_state
        CHECK (
            state IN ('NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT')
        ),

    CONSTRAINT ck_customer_profile_emergency_phone_format
        CHECK (emergency_contact_phone ~ '^0[0-9]{9}$'),

    -- Called when the parent can't be reached, so not the parent's number.
    CONSTRAINT ck_customer_profile_emergency_phone_distinct
        CHECK (emergency_contact_phone <> phone),

    CONSTRAINT ck_customer_profile_emergency_relation_other
        CHECK (
            (emergency_contact_relation = 'other')
                = (NULLIF(btrim(emergency_contact_relation_other), '') IS NOT NULL)
        )
);

CREATE TRIGGER trg_customer_profile_updated_at
    BEFORE UPDATE ON public.customer_profile
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- What a family accepted at sign-up stays on record.
CREATE FUNCTION public.enforce_customer_profile_terms_fixed()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.terms_document_id IS DISTINCT FROM OLD.terms_document_id THEN
        RAISE EXCEPTION 'The terms a family accepted can''t be changed'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_customer_profile_terms_fixed',
                  TABLE = 'customer_profile',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_customer_profile_terms_fixed
    BEFORE UPDATE ON public.customer_profile
    FOR EACH ROW EXECUTE FUNCTION public.enforce_customer_profile_terms_fixed();

-- Families own their emergency contact: anyone else with a session (an
-- admin correcting the family's phone or address) can't set or change it.
-- Server code with no session is trusted.
CREATE FUNCTION public.enforce_emergency_contact_owner()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
    v_changed BOOLEAN;
BEGIN
    IF auth.current_user_id() IS NULL OR auth.current_user_id() = NEW.user_id THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'INSERT' THEN
        v_changed := NEW.emergency_contact_name IS NOT NULL
            OR NEW.emergency_contact_phone IS NOT NULL
            OR NEW.emergency_contact_relation IS NOT NULL
            OR NEW.emergency_contact_relation_other IS NOT NULL;
    ELSE
        v_changed := (NEW.emergency_contact_name, NEW.emergency_contact_phone,
                      NEW.emergency_contact_relation, NEW.emergency_contact_relation_other)
            IS DISTINCT FROM
                     (OLD.emergency_contact_name, OLD.emergency_contact_phone,
                      OLD.emergency_contact_relation, OLD.emergency_contact_relation_other);
    END IF;

    IF v_changed THEN
        RAISE EXCEPTION 'Only the family can change their emergency contact'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_customer_profile_emergency_family_only',
                  TABLE = 'customer_profile',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_customer_profile_emergency_owner
    BEFORE INSERT OR UPDATE ON public.customer_profile
    FOR EACH ROW EXECUTE FUNCTION public.enforce_emergency_contact_owner();


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

    -- What staff asked the family for. Kept while the child is back in
    -- review (so staff can see what they asked), cleared on approval.
    documentation_request TEXT,

    updated_at TIMESTAMPTZ,
    -- The staff member who made the latest decision. NULL while the child
    -- waits for review (trg_child_profile_medical_review clears it).
    updated_by_user_id UUID,

    CONSTRAINT fk_child_medical_state_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_child_medical_state_updated_by
        FOREIGN KEY (updated_by_user_id)
        REFERENCES auth.users (id),

    -- Asking for documentation means saying what's needed.
    CONSTRAINT ck_child_medical_state_documentation_request
        CHECK (
            review_status <> 'documentation_requested'
            OR NULLIF(btrim(documentation_request), '') IS NOT NULL
        ),

    -- Nothing is outstanding once a child is approved or needs no review.
    CONSTRAINT ck_child_medical_state_request_cleared
        CHECK (
            review_status NOT IN ('approved', 'not_required')
            OR documentation_request IS NULL
        )
);

CREATE TRIGGER trg_child_medical_state_updated_at
    BEFORE UPDATE ON public.child_medical_state
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- Who may move a child's review where. RLS already limits writes to staff
-- (schema/0005); this pins down what each side may do:
--
--   * staff decide: approve, or request documentation (from pending,
--     documentation_requested or approved, e.g. an action plan has
--     expired). The decision is recorded against them, and approval
--     clears the request. They can also reopen an approved child
--     (approved -> pending; the service messages the family): it waits for review
--     again, with no reviewer, like a family's change. Existing bookings
--     stay; new ones wait for approval (the booking rules).
--   * the child's details decide when a review is needed: only
--     trg_child_profile_medical_review and trg_child_documents_medical_review
--     send a child back to pending, from a family's session.
--   * not_required is only ever set when a child is added.
--
-- Writes with no user session are trusted server code (migrations,
-- maintenance) and aren't limited.
--
-- SECURITY DEFINER: reads the child's location past RLS.
CREATE FUNCTION public.enforce_medical_review_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_id UUID := auth.current_user_id();
    v_is_staff BOOLEAN;
BEGIN
    IF v_user_id IS NULL
       OR (
           NEW.review_status IS NOT DISTINCT FROM OLD.review_status
           AND NEW.documentation_request IS NOT DISTINCT FROM OLD.documentation_request
       )
    THEN
        RETURN NEW;
    END IF;

    -- Medical approval is an admin responsibility (docs/portals.md).
    SELECT auth.is_location_admin(cp.location_id)
    INTO v_is_staff
    FROM public.child_profile cp
    WHERE cp.id = NEW.child_id;

    IF v_is_staff THEN
        -- Reopening an approved child: back in the queue, nothing asked.
        IF NEW.review_status = 'pending' AND OLD.review_status = 'approved' THEN
            NEW.documentation_request := NULL;
            NEW.updated_by_user_id := NULL;

            RETURN NEW;
        END IF;

        IF NEW.review_status NOT IN ('approved', 'documentation_requested') THEN
            RAISE EXCEPTION 'Staff can only approve child %, request documentation, or reopen an approval', NEW.child_id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_child_medical_state_staff_decision',
                      TABLE = 'child_medical_state',
                      SCHEMA = 'public';
        END IF;

        IF NEW.review_status = 'approved' THEN
            NEW.documentation_request := NULL;
        ELSE
            NEW.documentation_request := NULLIF(btrim(NEW.documentation_request), '');
        END IF;

        NEW.updated_by_user_id := v_user_id;

    ELSIF NEW.review_status <> 'pending'
       OR NEW.documentation_request IS DISTINCT FROM OLD.documentation_request
    THEN
        RAISE EXCEPTION 'Only staff can decide child %''s medical review', NEW.child_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_medical_state_staff_decision',
                  TABLE = 'child_medical_state',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_child_medical_state_rules
    BEFORE UPDATE ON public.child_medical_state
    FOR EACH ROW EXECUTE FUNCTION public.enforce_medical_review_rules();

-- A child's medical review follows their medical details, so it can't be
-- skipped or set by the family (who can only read child_medical_state,
-- schema/0005):
--
--   * a new child gets a review state: pending if any medical, allergy or
--     medication details were given, otherwise not_required
--   * any change to those details (adding, editing or clearing them) sends
--     the child back to pending for staff to review again
--   * so does uploading or removing a document
--     (trg_child_documents_medical_review, below)
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

-- Staff's internal notes about a child (slice 4-5): written and deleted by
-- admins on the website (child_notes c/d), read there and by staff at the
-- staff kiosk (child_notes r). Never shown to the family: RLS lets only
-- location staff and above see them (schema/0005). A note can't be
-- changed once saved (trg_child_notes_rules): a mistake is deleted and
-- written again, so what staff read is what was written.
CREATE TABLE public.child_notes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    child_id UUID NOT NULL,

    note TEXT NOT NULL,

    -- The writer, from the session (trg_child_notes_rules).
    created_by_user_id UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_child_notes_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_child_notes_created_by
        FOREIGN KEY (created_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT ck_child_notes_note
        CHECK (btrim(note) <> '')
);

CREATE INDEX ix_child_notes_child
    ON public.child_notes (child_id, created_at DESC);

-- The writer is whoever is logged in, and a saved note is fixed.
CREATE FUNCTION public.enforce_child_note_rules()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'UPDATE' THEN
        RAISE EXCEPTION 'A note can''t be changed once saved'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_notes_fixed',
                  TABLE = 'child_notes',
                  SCHEMA = 'public';
    END IF;

    NEW.created_by_user_id := COALESCE(auth.current_user_id(), NEW.created_by_user_id);
    NEW.created_at := now();

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_child_notes_rules
    BEFORE INSERT OR UPDATE ON public.child_notes
    FOR EACH ROW EXECUTE FUNCTION public.enforce_child_note_rules();


-- =====================================================
-- AUTHORIZED PICKUP PERSONS
-- =====================================================

-- Who may collect a family's children at a location: the account holder
-- plus up to three people the family adds. Everyone on the list may collect
-- every child on the account. Each person is also a kiosk login (phone and
-- 4-digit PIN) for signing children in and out on a registered device.
--
--   * a phone number and an email each belong to one family across the
--     whole tenant (the same family may be listed at several locations)
--   * the account holder's row is kept in sync with their name, login email
--     and profile phone (sync_account_holder_pickups); families can't edit
--     or remove it
--   * releasing a child needs staff approval: checking photo ID approves
--     the person automatically; staff can also approve someone without ID
--     (e.g. they're known to the centre). A new name or phone clears both.
--     Only staff set these (trg_authorized_pickup_persons_rules).
--
-- Kiosk PIN: staff never handle PINs. A random PIN is issued by
-- issue_pickup_pin() and emailed to the person (never shown in the app):
-- when they're added, when their email changes, and for the account holder
-- after their first child is added. Only its hash is stored. pin_hash NULL
-- means none issued yet. An issued PIN must be changed at the next kiosk
-- login (pin_change_required); after that, changes and "forgot PIN" happen
-- only at the kiosk (a new PIN emailed). An issued PIN that's never used
-- stops working 30 days after pin_issued_at (checked by the kiosk login;
-- docs/email-policy.md, section 4). Five wrong PINs lock the person
-- (pin_locked_at), not the device, until a reset.
CREATE TABLE public.authorized_pickup_persons (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,
    -- Set from the location by trg_authorized_pickup_persons_rules, for the
    -- tenant-wide phone and email rules.
    tenant_id UUID NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    -- Digits only, so formatting can't get around the phone rules.
    phone VARCHAR(15) NOT NULL,
    -- Where kiosk PINs are sent. Compared case-insensitively.
    email VARCHAR(255) NOT NULL,

    relation public.pickup_relation_enum NOT NULL,
    relation_other VARCHAR(100),

    -- The account holder's declarations when adding the person.
    consent_confirmed_at TIMESTAMPTZ,
    adult_confirmed_at TIMESTAMPTZ,

    -- Staff checked their photo ID.
    identity_verified_at TIMESTAMPTZ,
    identity_verified_by_user_id UUID,

    -- Staff approved them to collect children (set by an ID check, or on
    -- its own without ID). The kiosk only lets approved people sign out.
    staff_approved_at TIMESTAMPTZ,
    staff_approved_by_user_id UUID,

    pin_hash TEXT,
    pin_change_required BOOLEAN NOT NULL DEFAULT TRUE,
    -- When the current PIN was issued (emailed), for the 30-day limit on
    -- a setup PIN that's never been used.
    pin_issued_at TIMESTAMPTZ,
    failed_pin_attempts SMALLINT NOT NULL DEFAULT 0,
    pin_locked_at TIMESTAMPTZ,
    -- The last "forgot PIN" at the kiosk, for rate limiting resets.
    pin_reset_requested_at TIMESTAMPTZ,

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

    CONSTRAINT fk_authorized_pickup_persons_approved_by
        FOREIGN KEY (staff_approved_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT ck_authorized_pickup_persons_phone_format
        CHECK (phone ~ '^[0-9]{8,15}$'),

    CONSTRAINT ck_authorized_pickup_persons_email_format
        CHECK (email ~ '^[^@\s]+@[^@\s]+\.[^@\s]+$'),

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
        WHERE (is_active),

    -- The same for emails (a PIN reset must find one person's family).
    CONSTRAINT ex_authorized_pickup_persons_tenant_email
        EXCLUDE USING gist (
            tenant_id WITH =,
            (lower(email)) WITH =,
            user_id WITH <>
        )
        WHERE (is_active)
);

-- A family lists a phone number, and an email, once.
CREATE UNIQUE INDEX uq_authorized_pickup_persons_family_phone
    ON public.authorized_pickup_persons (user_id, location_id, phone)
    WHERE is_active;

CREATE UNIQUE INDEX uq_authorized_pickup_persons_family_email
    ON public.authorized_pickup_persons (user_id, location_id, lower(email))
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
-- Who may set what (writes with no user session are trusted server code:
-- migrations, maintenance, and the kiosk functions):
--   * ID check and staff approval: only by staff at the staff kiosk (the
--     kiosk channel, docs/portals.md), never from the website, admins
--     included
--   * PIN fields: only issue_pickup_pin() and the kiosk, never a family or
--     staff member directly
CREATE FUNCTION public.enforce_pickup_person_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_session BOOLEAN := auth.current_user_id() IS NOT NULL;
    v_pin_writer BOOLEAN := current_setting('app.pin_writer', true) = 'on';
    v_others INTEGER;
BEGIN
    SELECT l.tenant_id
    INTO NEW.tenant_id
    FROM tenancy.locations l
    WHERE l.id = NEW.location_id;

    NEW.phone := regexp_replace(NEW.phone, '\D', '', 'g');
    NEW.email := btrim(NEW.email);

    -- ID check and approval at the staff kiosk need the staff member to be
    -- on shift (docs/portals.md); refused rather than ignored, so the kiosk
    -- can say why.
    IF TG_OP = 'UPDATE'
       AND v_user_session
       AND auth.current_channel() = 'kiosk'
       AND (NEW.identity_verified_at, NEW.staff_approved_at)
           IS DISTINCT FROM (OLD.identity_verified_at, OLD.staff_approved_at)
       AND NOT public.staff_on_shift(NEW.location_id, auth.current_user_id()) THEN
        RAISE EXCEPTION 'Staff must be on shift to check ID'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_staff_kiosk_on_shift',
                  TABLE = 'authorized_pickup_persons',
                  SCHEMA = 'public';
    END IF;

    -- ID check and approval: only staff at the staff kiosk set them.
    IF v_user_session AND NOT (
        auth.current_channel() = 'kiosk'
        AND auth.is_location_staff(NEW.location_id)
    ) THEN
        IF TG_OP = 'INSERT' THEN
            NEW.identity_verified_at := NULL;
            NEW.identity_verified_by_user_id := NULL;
            NEW.staff_approved_at := NULL;
            NEW.staff_approved_by_user_id := NULL;
        ELSE
            NEW.identity_verified_at := OLD.identity_verified_at;
            NEW.identity_verified_by_user_id := OLD.identity_verified_by_user_id;
            NEW.staff_approved_at := OLD.staff_approved_at;
            NEW.staff_approved_by_user_id := OLD.staff_approved_by_user_id;
        END IF;
    END IF;

    -- PIN fields: only through issue_pickup_pin() (or trusted code).
    IF v_user_session AND NOT v_pin_writer THEN
        IF TG_OP = 'INSERT' THEN
            NEW.pin_hash := NULL;
            NEW.pin_change_required := TRUE;
            NEW.pin_issued_at := NULL;
            NEW.failed_pin_attempts := 0;
            NEW.pin_locked_at := NULL;
            NEW.pin_reset_requested_at := NULL;
        ELSE
            NEW.pin_hash := OLD.pin_hash;
            NEW.pin_change_required := OLD.pin_change_required;
            NEW.pin_issued_at := OLD.pin_issued_at;
            NEW.failed_pin_attempts := OLD.failed_pin_attempts;
            NEW.pin_locked_at := OLD.pin_locked_at;
            NEW.pin_reset_requested_at := OLD.pin_reset_requested_at;
        END IF;
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- A different name or phone is a different person to check.
        IF NEW.first_name IS DISTINCT FROM OLD.first_name
           OR NEW.last_name IS DISTINCT FROM OLD.last_name
           OR NEW.phone IS DISTINCT FROM OLD.phone THEN
            NEW.identity_verified_at := NULL;
            NEW.identity_verified_by_user_id := NULL;
            NEW.staff_approved_at := NULL;
            NEW.staff_approved_by_user_id := NULL;
        END IF;

        -- A new email: the old PIN may have gone to the wrong address, so
        -- it stops working until a new one is issued (to the new address).
        IF lower(NEW.email) IS DISTINCT FROM lower(OLD.email) THEN
            NEW.pin_hash := NULL;
            NEW.pin_change_required := TRUE;
            NEW.pin_issued_at := NULL;
            NEW.failed_pin_attempts := 0;
            NEW.pin_locked_at := NULL;
        END IF;
    END IF;

    -- Checking ID approves the person (approval can also be given alone).
    IF NEW.identity_verified_at IS NOT NULL AND NEW.staff_approved_at IS NULL THEN
        NEW.staff_approved_at := NEW.identity_verified_at;
        NEW.staff_approved_by_user_id := NEW.identity_verified_by_user_id;
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

-- Issue a pickup person a new random 4-digit PIN: store its hash, require
-- it to be changed at the next kiosk login, clear any lock, and return the
-- PIN once so the caller can email it. It's never stored or shown anywhere
-- else. SECURITY DEFINER: the only way PIN fields change from a user
-- session (trg_authorized_pickup_persons_rules); it checks the caller can
-- reach the person first.
CREATE FUNCTION public.issue_pickup_pin(p_pickup_id UUID)
RETURNS text
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_pin TEXT;
BEGIN
    IF auth.current_user_id() IS NOT NULL AND NOT EXISTS (
        SELECT 1
        FROM public.authorized_pickup_persons p
        WHERE p.id = p_pickup_id
          AND p.is_active
          AND auth.can_access_location_row(p.location_id, p.user_id)
    ) THEN
        RAISE EXCEPTION 'Pickup person % not found', p_pickup_id
            USING ERRCODE = 'no_data_found';
    END IF;

    -- 0000-9999 from a cryptographic source (the modulo bias is negligible).
    v_pin := lpad(
        (('x' || encode(gen_random_bytes(2), 'hex'))::bit(16)::integer % 10000)::text,
        4,
        '0'
    );

    PERFORM set_config('app.pin_writer', 'on', true);

    UPDATE public.authorized_pickup_persons
    SET pin_hash = crypt(v_pin, gen_salt('bf')),
        pin_change_required = TRUE,
        pin_issued_at = now(),
        failed_pin_attempts = 0,
        pin_locked_at = NULL
    WHERE id = p_pickup_id;

    PERFORM set_config('app.pin_writer', 'off', true);

    RETURN v_pin;
END;
$$;

-- Keep a user's account holder rows (one per location where they're a
-- customer) matching their name, login email and profile phone. Creates
-- them once the profile has a phone. A cleared phone leaves the rows as
-- they are. SECURITY DEFINER: writes the rows past RLS for the trigger
-- callers below.
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
    v_email VARCHAR(255);
    v_location_id UUID;
BEGIN
    SELECT NULLIF(regexp_replace(cp.phone, '\D', '', 'g'), '')
    INTO v_phone
    FROM public.customer_profile cp
    WHERE cp.user_id = p_user_id;

    IF v_phone IS NULL THEN
        RETURN;
    END IF;

    SELECT u.first_name, u.last_name, u.email
    INTO v_first_name, v_last_name, v_email
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
            email = v_email,
            phone = v_phone
        WHERE user_id = p_user_id
          AND location_id = v_location_id
          AND relation = 'account_holder'
          AND is_active
          AND (first_name, last_name, lower(email), phone)
              IS DISTINCT FROM (v_first_name, v_last_name, lower(v_email), v_phone);

        INSERT INTO public.authorized_pickup_persons (
            user_id, location_id, first_name, last_name, phone, email, relation
        )
        SELECT p_user_id, v_location_id, v_first_name, v_last_name, v_phone, v_email, 'account_holder'
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

-- Callers: a profile phone change, a name or email change, or becoming a
-- customer at another location.
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
    AFTER UPDATE OF first_name, last_name, email ON auth.users
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
    -- The family's file name, for display only. Never part of the object
    -- key (docs/child-document-retention-policy.md, section 4).
    filename VARCHAR(255) NOT NULL,

    -- Where the file lives. The provider and bucket are kept per row so
    -- files can move (another provider, or a tenant's own bucket) without
    -- a schema change. The key holds only IDs:
    --   pending/tenants/{tenant}/{document}                         uploading
    --   documents/tenants/{tenant}/locations/{location}/children/{child}/{document}
    storage_provider public.storage_provider_enum NOT NULL,
    storage_bucket VARCHAR(255) NOT NULL,
    storage_object_key TEXT NOT NULL,

    -- Checked against the stored file when the upload completes.
    content_type VARCHAR(100),
    size_bytes INTEGER,

    upload_status public.child_document_upload_status_enum
        NOT NULL DEFAULT 'pending',

    -- FALSE once the family removes it. The record (and file) is kept for
    -- the retention period either way.
    is_active BOOLEAN NOT NULL DEFAULT TRUE,

    -- Staff at the staff kiosk confirm they've printed it for the centre's
    -- action plan folder (public.set_document_printed). A new upload is a
    -- new document, so it starts unprinted.
    printed_at TIMESTAMPTZ,
    printed_by_user_id UUID,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_child_documents_printed_by
        FOREIGN KEY (printed_by_user_id)
        REFERENCES auth.users (id),

    CONSTRAINT ck_child_documents_printed_by
        CHECK ((printed_at IS NULL) = (printed_by_user_id IS NULL)),

    CONSTRAINT fk_child_documents_child
        FOREIGN KEY (child_id)
        REFERENCES public.child_profile (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_child_documents_uploaded_by
        FOREIGN KEY (uploaded_by_user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_child_documents_storage_object
        UNIQUE (storage_provider, storage_bucket, storage_object_key),

    -- PDFs and photos only (iPhones save photos as HEIC).
    CONSTRAINT ck_child_documents_content_type
        CHECK (
            content_type IS NULL
            OR content_type IN ('application/pdf', 'image/jpeg', 'image/png', 'image/heic')
        ),

    -- At most 10 MB.
    CONSTRAINT ck_child_documents_size
        CHECK (size_bytes IS NULL OR size_bytes BETWEEN 1 AND 10485760),

    -- An accepted file's type and size are known.
    CONSTRAINT ck_child_documents_uploaded_details
        CHECK (
            upload_status <> 'uploaded'
            OR (content_type IS NOT NULL AND size_bytes IS NOT NULL)
        )
);

CREATE INDEX idx_child_documents_child
    ON public.child_documents (child_id)
    WHERE is_active;

CREATE TRIGGER trg_child_documents_updated_at
    BEFORE UPDATE ON public.child_documents
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- The rules every write to a document goes through. SECURITY DEFINER:
-- reads the child past RLS.
--
-- From a user session:
--   * only the child's family adds or removes documents; staff and admins
--     read them (they review, they don't manage the family's records)
--   * a document is added to a current child, and recorded as uploaded by
--     whoever is adding it
--   * an upload finishes once: pending becomes uploaded or failed, and only
--     then may its file move (from pending/ to documents/)
--   * removing a document is final; the family uploads it again instead
--   * what it is and whose it is never change
--   * whether it's been printed is set only by staff at the staff kiosk,
--     through public.set_document_printed (app.print_writer), which may
--     change nothing else
--
-- Writes with no user session are trusted server code (maintenance, moving
-- files between buckets, the retention job) and aren't limited.
CREATE FUNCTION public.enforce_child_document_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_id UUID := auth.current_user_id();
    v_owner_id UUID;
    v_child_active BOOLEAN;
    v_child_found BOOLEAN;
BEGIN
    IF v_user_id IS NULL THEN
        RETURN NEW;
    END IF;

    IF TG_OP = 'UPDATE' AND current_setting('app.print_writer', true) = 'on' THEN
        IF (to_jsonb(NEW) - ARRAY['printed_at', 'printed_by_user_id', 'updated_at'])
           IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['printed_at', 'printed_by_user_id', 'updated_at']) THEN
            RAISE EXCEPTION 'Document % can''t be changed that way', NEW.id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_child_documents_change',
                      TABLE = 'child_documents',
                      SCHEMA = 'public';
        END IF;

        RETURN NEW;
    END IF;

    SELECT cp.user_id, cp.is_active
    INTO v_owner_id, v_child_active
    FROM public.child_profile cp
    WHERE cp.id = NEW.child_id;

    v_child_found := FOUND;

    -- An unknown child is left to fk_child_documents_child.
    IF v_child_found AND v_owner_id <> v_user_id THEN
        RAISE EXCEPTION 'Only the family can add or remove child %''s documents', NEW.child_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_documents_family_only',
                  TABLE = 'child_documents',
                  SCHEMA = 'public';
    END IF;

    IF TG_OP = 'INSERT' THEN
        IF v_child_found AND NOT v_child_active THEN
            RAISE EXCEPTION 'Child % has been removed', NEW.child_id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_child_documents_child_active',
                      TABLE = 'child_documents',
                      SCHEMA = 'public';
        END IF;

        NEW.uploaded_by_user_id := v_user_id;
        NEW.is_active := TRUE;
        NEW.printed_at := NULL;
        NEW.printed_by_user_id := NULL;

        RETURN NEW;
    END IF;

    IF NEW.child_id IS DISTINCT FROM OLD.child_id
       OR NEW.uploaded_by_user_id IS DISTINCT FROM OLD.uploaded_by_user_id
       OR NEW.document_type IS DISTINCT FROM OLD.document_type
       OR NEW.filename IS DISTINCT FROM OLD.filename
       OR NEW.storage_provider IS DISTINCT FROM OLD.storage_provider
       OR NEW.created_at IS DISTINCT FROM OLD.created_at
       OR NEW.printed_at IS DISTINCT FROM OLD.printed_at
       OR NEW.printed_by_user_id IS DISTINCT FROM OLD.printed_by_user_id
       -- An upload finishes once, and a removed document stays removed.
       OR (NEW.upload_status IS DISTINCT FROM OLD.upload_status AND OLD.upload_status <> 'pending')
       OR (NEW.is_active AND NOT OLD.is_active)
       -- The file only moves (and its details are only filled in) as the
       -- upload finishes.
       OR (
           OLD.upload_status <> 'pending'
           AND (
               NEW.storage_bucket IS DISTINCT FROM OLD.storage_bucket
               OR NEW.storage_object_key IS DISTINCT FROM OLD.storage_object_key
               OR NEW.content_type IS DISTINCT FROM OLD.content_type
               OR NEW.size_bytes IS DISTINCT FROM OLD.size_bytes
           )
       )
    THEN
        RAISE EXCEPTION 'Document % can''t be changed that way', NEW.id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_documents_change',
                  TABLE = 'child_documents',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_child_documents_rules
    BEFORE INSERT OR UPDATE ON public.child_documents
    FOR EACH ROW EXECUTE FUNCTION public.enforce_child_document_rules();

-- A staff member at the staff kiosk, on shift, ticks (or unticks, to
-- correct a mistake) that they've printed a current document for the
-- folder. Recorded against them. Only these two fields change.
CREATE FUNCTION public.set_document_printed(p_document_id UUID, p_printed BOOLEAN)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_id UUID := auth.current_user_id();
    v_location_id UUID;
BEGIN
    SELECT cp.location_id
    INTO v_location_id
    FROM public.child_documents d
    JOIN public.child_profile cp
        ON cp.id = d.child_id
    WHERE d.id = p_document_id
      AND d.is_active
      AND d.upload_status = 'uploaded';

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Document % not found', p_document_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_documents_printed_document',
                  TABLE = 'child_documents',
                  SCHEMA = 'public';
    END IF;

    IF v_user_id IS NULL
       OR auth.current_channel() <> 'kiosk'
       OR NOT auth.is_location_staff(v_location_id)
       OR NOT public.staff_on_shift(v_location_id, v_user_id) THEN
        RAISE EXCEPTION 'Only staff on shift at the staff kiosk mark documents printed'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_child_documents_printed_by_staff',
                  TABLE = 'child_documents',
                  SCHEMA = 'public';
    END IF;

    PERFORM set_config('app.print_writer', 'on', true);

    UPDATE public.child_documents
    SET printed_at = CASE WHEN p_printed THEN now() END,
        printed_by_user_id = CASE WHEN p_printed THEN v_user_id END
    WHERE id = p_document_id;

    PERFORM set_config('app.print_writer', '', true);
END;
$$;

-- Documents count as medical details: when one is accepted, or an
-- accepted one is removed, the child goes back to pending for staff to
-- review again (see sync_child_medical_review above). This is also how a
-- family answers a documentation request. Uploads still in progress, and
-- failed ones, don't count.
--
-- SECURITY DEFINER: writes child_medical_state past its staff-only write
-- policy.
CREATE FUNCTION public.sync_child_document_medical_review()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_counts BOOLEAN := NEW.is_active AND NEW.upload_status = 'uploaded';
    v_counted BOOLEAN := FALSE;
BEGIN
    IF TG_OP = 'UPDATE' THEN
        v_counted := OLD.is_active AND OLD.upload_status = 'uploaded';
    END IF;

    IF v_counts IS DISTINCT FROM v_counted THEN
        -- Not reviewed by anyone yet, so no reviewer.
        UPDATE public.child_medical_state
        SET review_status = 'pending',
            updated_by_user_id = NULL
        WHERE child_id = NEW.child_id
          AND review_status <> 'pending';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_child_documents_medical_review
    AFTER INSERT OR UPDATE OF upload_status, is_active
    ON public.child_documents
    FOR EACH ROW EXECUTE FUNCTION public.sync_child_document_medical_review();


-- =====================================================
-- LOCATION KIOSK DEVICES
-- =====================================================

-- A tablet at the centre's entrance. An admin adds it and gets a one-time
-- setup code (only its SHA-256 is kept, for 15 minutes); entering the code
-- on the tablet pairs it (kiosk_pair), and the tablet then holds a cookie
-- naming the device and its token_version. Revoking (is_active false) or
-- issuing a new code (token_version + 1) makes old cookies stop working.
CREATE TABLE public.location_kiosk_devices (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,

    kind public.kiosk_kind_enum NOT NULL,
    name TEXT NOT NULL,
    setup_secret_hash TEXT,
    setup_code_expires_at TIMESTAMPTZ,
    token_version INTEGER NOT NULL DEFAULT 1,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    paired_at TIMESTAMPTZ,
    last_used TIMESTAMPTZ,

    CONSTRAINT fk_location_kiosk_devices_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
);

-- One active kiosk of each kind per location; a revoked one doesn't count.
CREATE UNIQUE INDEX uq_location_kiosk_devices_active_kind
    ON public.location_kiosk_devices (location_id, kind)
    WHERE is_active;


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

    -- The tenant's Stripe account the payment was taken in (direct
    -- charges), set by trg_payment_attempts_account; its refunds go
    -- through the same account. NULL only for rows written by server code
    -- (seeds), which use the platform account.
    stripe_account_id VARCHAR(255),

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

-- A checkout goes to the tenant's Stripe account, and only while it can
-- take payments (tenancy.payments_account). Server code with no session
-- (seeds) is trusted and keeps what it gives.
CREATE FUNCTION public.set_payment_attempt_account()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF auth.current_user_id() IS NULL THEN
        RETURN NEW;
    END IF;

    NEW.stripe_account_id := tenancy.payments_account(NEW.location_id);

    IF NEW.stripe_account_id IS NULL THEN
        RAISE EXCEPTION 'Location % isn''t taking payments', NEW.location_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_payment_attempts_payments_enabled',
                  TABLE = 'payment_attempts',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_payment_attempts_account
    BEFORE INSERT ON public.payment_attempts
    FOR EACH ROW EXECUTE FUNCTION public.set_payment_attempt_account();


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

-- Cancelling without a refund (the family, or an admin for them; the same
-- rules for both): a confirmed, paid booking once the family's refund
-- window has closed (refund_cutoff_days before the day), until its session
-- starts (location time). Its place goes back; the money is kept, so it
-- stays PAID: CANCELLED and PAID means cancelled without a refund.
-- plpgsql so it can use effective_booking_status (schema/0009) at run time.
CREATE FUNCTION public.booking_is_cancellable(p_booking_id UUID)
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
          AND (now() AT TIME ZONE l.timezone)::date > d.service_date - lsc.refund_cutoff_days
          AND now() < (d.service_date + lsc.start_time) AT TIME ZONE l.timezone
          AND NOT EXISTS (
              SELECT 1
              FROM public.refunds r
              WHERE r.booking_id = b.id
                AND r.status IN ('PENDING', 'SUCCEEDED')
          )
    );
END;
$$;

-- Reinstating a booking cancelled without a refund: still CANCELLED and
-- PAID, until its session starts. The place must still be free, and the
-- usual booking rules apply again (trg_bookings_reinstate_rules).
CREATE FUNCTION public.booking_is_reinstatable(p_booking_id UUID)
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
          AND b.booking_status = 'CANCELLED'
          AND b.payment_status = 'PAID'
          AND now() < (d.service_date + lsc.start_time) AT TIME ZONE l.timezone
          AND NOT EXISTS (
              SELECT 1
              FROM public.refunds r
              WHERE r.booking_id = b.id
                AND r.status IN ('PENDING', 'SUCCEEDED')
          )
    );
END;
$$;

-- Cancelling (CONFIRMED -> CANCELLED, still PAID) and reinstating
-- (CANCELLED -> CONFIRMED) by a user must fit the windows above; stamped
-- with the database's clock. Server code with no session (payment and
-- refund webhooks) is trusted. A refund's cancel sets REFUNDED, so isn't
-- one of these.
CREATE FUNCTION public.enforce_booking_cancel_rules()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF auth.current_user_id() IS NULL THEN
        RETURN NEW;
    END IF;

    IF OLD.booking_status = 'CONFIRMED'
       AND NEW.booking_status = 'CANCELLED'
       AND NEW.payment_status = 'PAID' THEN
        IF NOT public.booking_is_cancellable(OLD.id) THEN
            RAISE EXCEPTION 'Booking % can''t be cancelled now', OLD.id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_cancel_window',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;

        NEW.cancelled_at := now();
    ELSIF OLD.booking_status = 'CANCELLED' AND NEW.booking_status = 'CONFIRMED' THEN
        IF NOT public.booking_is_reinstatable(OLD.id) THEN
            RAISE EXCEPTION 'Booking % can''t be reinstated', OLD.id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_reinstate_window',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;

        NEW.cancelled_at := NULL;
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_bookings_cancel_rules
    BEFORE UPDATE OF booking_status ON public.bookings
    FOR EACH ROW EXECUTE FUNCTION public.enforce_booking_cancel_rules();

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

    -- Admins (on the website or at the staff kiosk) can refund up to and
    -- including the session day; families until their cutoff.
    IF NOT public.booking_is_refundable(
        NEW.booking_id,
        COALESCE(auth.is_location_admin(NEW.location_id), FALSE)
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

    -- Paid, but with nothing in Stripe to refund against (e.g. marked paid
    -- without a card payment). Its own name, so it isn't reported as the
    -- refund window.
    IF NEW.payment_attempt_id IS NULL THEN
        RAISE EXCEPTION 'Booking % has no refundable payment', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_refunds_card_payment',
                  TABLE = 'refunds',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_refunds_rules
    BEFORE INSERT ON public.refunds
    FOR EACH ROW EXECUTE FUNCTION public.enforce_refund_rules();


-- When children can be signed in and out for a session, at either kiosk:
-- from 2 hours before it starts to 2 hours after it ends, on its day, at
-- the location's time. NULLs when the location doesn't enforce it
-- (tenancy.locations.kiosk_enforce_service_times). Used by the attendance
-- trigger (the rule) and both kiosks (what they show).
CREATE FUNCTION public.service_day_signing_window(
    p_location_service_day_id UUID,
    OUT opens_at TIMESTAMPTZ,
    OUT closes_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT
        CASE WHEN l.kiosk_enforce_service_times
            THEN ((d.service_date + lsc.start_time) AT TIME ZONE l.timezone) - interval '2 hours'
        END,
        CASE WHEN l.kiosk_enforce_service_times
            THEN ((d.service_date + lsc.end_time) AT TIME ZONE l.timezone) + interval '2 hours'
        END
    FROM public.location_service_days d
    JOIN public.location_service_config lsc
        ON lsc.location_service_id = d.location_service_id
    JOIN tenancy.locations l
        ON l.id = d.location_id
    WHERE d.id = p_location_service_day_id;
$$;

-- The same, for a booking's session.
CREATE FUNCTION public.booking_signing_window(
    p_booking_id UUID,
    OUT opens_at TIMESTAMPTZ,
    OUT closes_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT w.opens_at, w.closes_at
    FROM public.bookings b
    CROSS JOIN LATERAL public.service_day_signing_window(b.location_service_day_id) w
    WHERE b.id = p_booking_id;
$$;

-- An admin switches the family kiosk's service times on or off for their
-- location. Only that column: admins don't otherwise write locations.
CREATE FUNCTION public.set_kiosk_enforce_service_times(p_location_id UUID, p_enabled BOOLEAN)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT auth.is_location_admin(p_location_id) THEN
        RAISE EXCEPTION 'Only the location''s admins can change kiosk settings'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_locations_kiosk_settings_admin',
                  TABLE = 'locations',
                  SCHEMA = 'tenancy';
    END IF;

    UPDATE tenancy.locations
    SET kiosk_enforce_service_times = p_enabled
    WHERE id = p_location_id;
END;
$$;


-- =====================================================
-- ATTENDANCE RECORDS
-- =====================================================

CREATE TABLE public.attendance_records (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    booking_id UUID NOT NULL,

    -- Arrival: signed in by a staff member, or by someone on the family's
    -- pickup list at the kiosk.
    signed_in_at TIMESTAMPTZ,
    signed_in_by_user_id UUID,
    signed_in_by_pickup_person_id UUID,
    signed_in_kiosk_device_id UUID,

    -- Departure: recorded by a staff member or at the kiosk, and collected
    -- by an approved pickup person, or (staff only) released to someone
    -- else after checking with the account holder (a one-off release), or
    -- (staff only, before school care) sent to school.
    signed_out_at TIMESTAMPTZ,
    signed_out_by_user_id UUID,
    signed_out_kiosk_device_id UUID,
    collected_by_pickup_person_id UUID,
    released_to_name VARCHAR(200),
    release_note TEXT,
    sent_to_school BOOLEAN NOT NULL DEFAULT FALSE,

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

    CONSTRAINT fk_attendance_records_signed_in_by_pickup_person
        FOREIGN KEY (signed_in_by_pickup_person_id)
        REFERENCES public.authorized_pickup_persons (id),

    CONSTRAINT fk_attendance_records_collected_by
        FOREIGN KEY (collected_by_pickup_person_id)
        REFERENCES public.authorized_pickup_persons (id),

    CONSTRAINT fk_attendance_records_signed_in_kiosk
        FOREIGN KEY (signed_in_kiosk_device_id)
        REFERENCES public.location_kiosk_devices (id),

    CONSTRAINT fk_attendance_records_signed_out_kiosk
        FOREIGN KEY (signed_out_kiosk_device_id)
        REFERENCES public.location_kiosk_devices (id),

    -- Signed in at a kiosk, by exactly one: a staff member (staff kiosk)
    -- or a pickup person (family kiosk).
    CONSTRAINT ck_attendance_records_signed_in_by
        CHECK (
            CASE WHEN signed_in_at IS NULL
                THEN num_nonnulls(signed_in_by_user_id, signed_in_by_pickup_person_id, signed_in_kiosk_device_id) = 0
                ELSE num_nonnulls(signed_in_by_user_id, signed_in_by_pickup_person_id) = 1
                     AND signed_in_kiosk_device_id IS NOT NULL
            END
        ),

    -- Signed out at a kiosk (by a staff member at the staff kiosk, or the
    -- collector themselves at the family kiosk), and gone by exactly one
    -- way: an approved pickup person, a named one-off release, or sent to
    -- school.
    CONSTRAINT ck_attendance_records_signed_out_by
        CHECK (
            CASE WHEN signed_out_at IS NULL
                THEN num_nonnulls(signed_out_by_user_id, signed_out_kiosk_device_id, collected_by_pickup_person_id, released_to_name, release_note) = 0
                     AND NOT sent_to_school
                ELSE signed_out_kiosk_device_id IS NOT NULL
            END
        ),

    CONSTRAINT ck_attendance_records_collected_by
        CHECK (
            signed_out_at IS NULL
            OR num_nonnulls(
                collected_by_pickup_person_id,
                NULLIF(btrim(released_to_name), ''),
                NULLIF(sent_to_school, FALSE)
            ) = 1
        ),

    -- Only staff send a child to school.
    CONSTRAINT ck_attendance_records_to_school_by_staff
        CHECK (NOT sent_to_school OR signed_out_by_user_id IS NOT NULL),

    -- Only staff release a child to someone who isn't on the list.
    CONSTRAINT ck_attendance_records_release_by_staff
        CHECK (released_to_name IS NULL OR signed_out_by_user_id IS NOT NULL),

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

-- The rules every attendance write goes through. SECURITY DEFINER: reads
-- the booking, its day, the device and the family's pickup people past RLS.
--
--   * attendance is only written at a kiosk (docs/portals.md): by a staff
--     member at the location's staff kiosk (the kiosk channel, their PIN
--     checked for the request; recorded against them and the device), or
--     by a pickup person at the family kiosk (the kiosk_* functions, no
--     user session). Never from the website, admins included.
--   * a pickup person signs at the family kiosk; staff at the staff kiosk
--   * only a confirmed booking is signed in or out, never before the
--     session's day (the family kiosk only offers today's; staff can also
--     fix earlier days)
--   * pickup people are on this family's list at this location, and only
--     an approved one (staff_approved_at) collects a child
CREATE FUNCTION public.enforce_attendance_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_id UUID := auth.current_user_id();
    v_device_id UUID := auth.current_kiosk_device_id();
    v_booking_status public.booking_status_enum;
    v_family_id UUID;
    v_location_id UUID;
    v_service_date DATE;
    v_service_code TEXT;
    v_today DATE;
    v_opens_at TIMESTAMPTZ;
    v_closes_at TIMESTAMPTZ;
BEGIN
    SELECT b.booking_status, b.user_id, b.location_id, d.service_date, st.code,
           (now() AT TIME ZONE l.timezone)::date
    INTO v_booking_status, v_family_id, v_location_id, v_service_date, v_service_code, v_today
    FROM public.bookings b
    JOIN public.location_service_days d
        ON d.id = b.location_service_day_id
    JOIN public.location_services ls
        ON ls.id = d.location_service_id
    JOIN public.service_types st
        ON st.id = ls.service_type_id
    JOIN tenancy.locations l
        ON l.id = b.location_id
    WHERE b.id = NEW.booking_id;

    -- An unknown booking is left to fk_attendance_records_booking.
    IF NOT FOUND THEN
        RETURN NEW;
    END IF;

    IF v_user_id IS NOT NULL THEN
        IF auth.current_channel() <> 'kiosk'
           OR v_device_id IS NULL
           OR NOT auth.is_location_staff(v_location_id) THEN
            RAISE EXCEPTION 'Attendance for booking % is only recorded at a kiosk', NEW.booking_id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_attendance_records_kiosk_only',
                      TABLE = 'attendance_records',
                      SCHEMA = 'public';
        END IF;

        IF NOT public.staff_on_shift(v_location_id, v_user_id) THEN
            RAISE EXCEPTION 'Staff must be on shift to record attendance'
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_staff_kiosk_on_shift',
                      TABLE = 'attendance_records',
                      SCHEMA = 'public';
        END IF;

        -- Who did it, and where: the staff member and their kiosk.
        IF NEW.signed_in_at IS DISTINCT FROM (CASE WHEN TG_OP = 'UPDATE' THEN OLD.signed_in_at END)
           AND NEW.signed_in_at IS NOT NULL THEN
            NEW.signed_in_by_user_id := v_user_id;
            NEW.signed_in_by_pickup_person_id := NULL;
            NEW.signed_in_kiosk_device_id := v_device_id;
        END IF;

        IF NEW.signed_out_at IS DISTINCT FROM (CASE WHEN TG_OP = 'UPDATE' THEN OLD.signed_out_at END)
           AND NEW.signed_out_at IS NOT NULL THEN
            NEW.signed_out_by_user_id := v_user_id;
            NEW.signed_out_kiosk_device_id := v_device_id;
        END IF;
    END IF;

    IF v_booking_status <> 'CONFIRMED' THEN
        RAISE EXCEPTION 'Booking % is not confirmed', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_booking_confirmed',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    IF v_service_date > v_today THEN
        RAISE EXCEPTION 'Booking % is on a later day', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_service_day',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    -- Signing in and out only around the session, at either kiosk (when
    -- the location enforces it), by the time recorded: staff correcting an
    -- earlier day give when it happened.
    SELECT w.opens_at, w.closes_at
    INTO v_opens_at, v_closes_at
    FROM public.booking_signing_window(NEW.booking_id) w;

    IF v_opens_at IS NOT NULL AND EXISTS (
        SELECT 1
        FROM (VALUES
            (NEW.signed_in_at, NEW.signed_in_at IS DISTINCT FROM (CASE WHEN TG_OP = 'UPDATE' THEN OLD.signed_in_at END)),
            (NEW.signed_out_at, NEW.signed_out_at IS DISTINCT FROM (CASE WHEN TG_OP = 'UPDATE' THEN OLD.signed_out_at END))
        ) AS signing(at, changed)
        WHERE signing.changed
          AND signing.at IS NOT NULL
          AND NOT signing.at BETWEEN v_opens_at AND v_closes_at
    ) THEN
        RAISE EXCEPTION 'Booking % is outside its kiosk sign in and out times', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_service_window',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    -- Children are sent to school only from before school care.
    IF NEW.sent_to_school
       AND NOT (TG_OP = 'UPDATE' AND OLD.sent_to_school)
       AND v_service_code <> 'before_school_care' THEN
        RAISE EXCEPTION 'Booking % is not before school care', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_to_school_service',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    -- Each kiosk does its own kind of signing, at its own location.
    IF EXISTS (
        SELECT 1
        FROM (VALUES
            (NEW.signed_in_kiosk_device_id, NEW.signed_in_by_user_id IS NOT NULL),
            (NEW.signed_out_kiosk_device_id, NEW.signed_out_by_user_id IS NOT NULL)
        ) AS signing(device_id, by_staff)
        WHERE signing.device_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM public.location_kiosk_devices k
              WHERE k.id = signing.device_id
                AND k.location_id = v_location_id
                AND k.kind = CASE WHEN signing.by_staff THEN 'staff' ELSE 'family' END::public.kiosk_kind_enum
          )
    ) THEN
        RAISE EXCEPTION 'Wrong kiosk for booking %', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_kiosk_kind',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    IF EXISTS (
        SELECT 1
        FROM unnest(ARRAY[NEW.signed_in_by_pickup_person_id, NEW.collected_by_pickup_person_id]) AS person(id)
        WHERE person.id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM public.authorized_pickup_persons p
              WHERE p.id = person.id
                AND p.user_id = v_family_id
                AND p.location_id = v_location_id
                AND p.is_active
          )
    ) THEN
        RAISE EXCEPTION 'Not on the pickup list for booking %', NEW.booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_family_person',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    IF NEW.collected_by_pickup_person_id IS DISTINCT FROM (CASE WHEN TG_OP = 'UPDATE' THEN OLD.collected_by_pickup_person_id END)
       AND NEW.collected_by_pickup_person_id IS NOT NULL
       AND NOT EXISTS (
           SELECT 1
           FROM public.authorized_pickup_persons p
           WHERE p.id = NEW.collected_by_pickup_person_id
             AND p.staff_approved_at IS NOT NULL
       ) THEN
        RAISE EXCEPTION 'Pickup person % is not approved to collect children', NEW.collected_by_pickup_person_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_collector_approved',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_attendance_records_rules
    BEFORE INSERT OR UPDATE ON public.attendance_records
    FOR EACH ROW EXECUTE FUNCTION public.enforce_attendance_rules();


-- =====================================================
-- KIOSK
-- =====================================================
-- The kiosk tablet has no user session, so RLS shows it nothing. These
-- functions are its only way in, each doing one thing for one location
-- (from the device's cookie) and one pickup person (from their PIN login).
-- SECURITY DEFINER: they read and write past RLS, within those limits.
-- The API checks the device and the person's session before calling them.

-- Pair a tablet with its one-time setup code (15 minutes, single use).
-- Returns the device, its kind and the token version its cookie must carry.
CREATE FUNCTION public.kiosk_pair(p_location_id UUID, p_code TEXT)
RETURNS TABLE (device_id UUID, kind public.kiosk_kind_enum, token_version INTEGER)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    UPDATE public.location_kiosk_devices d
    SET paired_at = now(),
        last_used = now(),
        setup_secret_hash = NULL,
        setup_code_expires_at = NULL
    WHERE d.location_id = p_location_id
      AND d.is_active
      AND d.setup_secret_hash = encode(digest(upper(btrim(p_code)), 'sha256'), 'hex')
      AND d.setup_code_expires_at > now()
    RETURNING d.id, d.kind, d.token_version;
$$;

-- The location and kind of a paired, active device whose cookie is
-- current; no row otherwise. Records when it was last used.
CREATE FUNCTION public.kiosk_device(p_device_id UUID, p_token_version INTEGER)
RETURNS TABLE (location_id UUID, kind public.kiosk_kind_enum)
LANGUAGE sql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    UPDATE public.location_kiosk_devices d
    SET last_used = now()
    WHERE d.id = p_device_id
      AND d.token_version = p_token_version
      AND d.is_active
      AND d.paired_at IS NOT NULL
    RETURNING d.location_id, d.kind;
$$;

-- A pickup person logging in with their mobile and PIN.
--   ok        logged in (pin_change_required: choose a new PIN first)
--   invalid   wrong number or PIN (the same either way)
--   locked    5 wrong PINs in a row; "Forgot PIN" unlocks
--   expired   a setup PIN not used within 30 days; "Forgot PIN" for a new one
CREATE FUNCTION public.kiosk_login(p_location_id UUID, p_phone TEXT, p_pin TEXT)
RETURNS TABLE (result TEXT, pickup_person_id UUID, first_name TEXT, pin_change_required BOOLEAN)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_person public.authorized_pickup_persons%ROWTYPE;
    v_failures SMALLINT;
BEGIN
    SELECT *
    INTO v_person
    FROM public.authorized_pickup_persons p
    WHERE p.location_id = p_location_id
      AND p.phone = regexp_replace(p_phone, '\D', '', 'g')
      AND p.is_active
    FOR UPDATE;

    IF NOT FOUND OR v_person.pin_hash IS NULL THEN
        RETURN QUERY SELECT 'invalid'::text, NULL::uuid, NULL::text, NULL::boolean;
        RETURN;
    END IF;

    IF v_person.pin_locked_at IS NOT NULL THEN
        RETURN QUERY SELECT 'locked'::text, NULL::uuid, NULL::text, NULL::boolean;
        RETURN;
    END IF;

    PERFORM set_config('app.pin_writer', 'on', true);

    IF crypt(p_pin, v_person.pin_hash) <> v_person.pin_hash THEN
        v_failures := v_person.failed_pin_attempts + 1;

        UPDATE public.authorized_pickup_persons
        SET failed_pin_attempts = v_failures,
            pin_locked_at = CASE WHEN v_failures >= 5 THEN now() END
        WHERE id = v_person.id;

        PERFORM set_config('app.pin_writer', 'off', true);

        RETURN QUERY SELECT
            CASE WHEN v_failures >= 5 THEN 'locked' ELSE 'invalid' END,
            NULL::uuid, NULL::text, NULL::boolean;
        RETURN;
    END IF;

    UPDATE public.authorized_pickup_persons
    SET failed_pin_attempts = 0
    WHERE id = v_person.id;

    PERFORM set_config('app.pin_writer', 'off', true);

    IF v_person.pin_change_required
       AND v_person.pin_issued_at < now() - interval '30 days' THEN
        RETURN QUERY SELECT 'expired'::text, NULL::uuid, NULL::text, NULL::boolean;
        RETURN;
    END IF;

    RETURN QUERY SELECT
        'ok'::text, v_person.id, v_person.first_name::text, v_person.pin_change_required;
END;
$$;

-- A logged-in pickup person choosing their own PIN: 4 digits, not the
-- one they have. Clears the change-required flag.
CREATE FUNCTION public.kiosk_change_pin(p_location_id UUID, p_pickup_person_id UUID, p_new_pin TEXT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_pin_hash TEXT;
BEGIN
    IF p_new_pin IS NULL OR p_new_pin !~ '^\d{4}$' THEN
        RAISE EXCEPTION 'A PIN is 4 digits'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_authorized_pickup_persons_pin_format',
                  TABLE = 'authorized_pickup_persons',
                  SCHEMA = 'public';
    END IF;

    SELECT p.pin_hash
    INTO v_pin_hash
    FROM public.authorized_pickup_persons p
    WHERE p.id = p_pickup_person_id
      AND p.location_id = p_location_id
      AND p.is_active
      AND p.pin_locked_at IS NULL
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Pickup person % not found', p_pickup_person_id
            USING ERRCODE = 'no_data_found';
    END IF;

    IF v_pin_hash IS NOT NULL AND crypt(p_new_pin, v_pin_hash) = v_pin_hash THEN
        RAISE EXCEPTION 'The new PIN is the current one'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_authorized_pickup_persons_pin_reused',
                  TABLE = 'authorized_pickup_persons',
                  SCHEMA = 'public';
    END IF;

    PERFORM set_config('app.pin_writer', 'on', true);

    UPDATE public.authorized_pickup_persons
    SET pin_hash = crypt(p_new_pin, gen_salt('bf')),
        pin_change_required = FALSE,
        failed_pin_attempts = 0
    WHERE id = p_pickup_person_id;

    PERFORM set_config('app.pin_writer', 'off', true);
END;
$$;

-- "Forgot PIN" at the kiosk: a new setup PIN for the person with this
-- mobile, returned once so the API can email it (KioskPinEmail). Nothing is
-- returned for an unknown number, or within 20 minutes of the last reset
-- (about 3 an hour); the kiosk says the same either way. A reset also
-- clears a lock (issue_pickup_pin).
CREATE FUNCTION public.kiosk_forgot_pin(p_location_id UUID, p_phone TEXT)
RETURNS TABLE (pickup_person_id UUID, email TEXT, first_name TEXT, pin TEXT)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_person public.authorized_pickup_persons%ROWTYPE;
BEGIN
    SELECT *
    INTO v_person
    FROM public.authorized_pickup_persons p
    WHERE p.location_id = p_location_id
      AND p.phone = regexp_replace(p_phone, '\D', '', 'g')
      AND p.is_active
    FOR UPDATE;

    IF NOT FOUND
       OR v_person.pin_reset_requested_at > now() - interval '20 minutes' THEN
        RETURN;
    END IF;

    PERFORM set_config('app.pin_writer', 'on', true);

    UPDATE public.authorized_pickup_persons
    SET pin_reset_requested_at = now()
    WHERE id = v_person.id;

    PERFORM set_config('app.pin_writer', 'off', true);

    RETURN QUERY SELECT
        v_person.id,
        v_person.email::text,
        v_person.first_name::text,
        public.issue_pickup_pin(v_person.id);
END;
$$;

-- Today's sessions for the children a pickup person may collect: their
-- family's confirmed bookings at this location for today (the location's
-- timezone), with where each one is up to. Children by first name and
-- initial only: the screen is in a public entrance.
CREATE FUNCTION public.kiosk_family_today(p_location_id UUID, p_pickup_person_id UUID)
RETURNS TABLE (
    booking_id UUID,
    child_first_name TEXT,
    child_last_initial TEXT,
    service_name TEXT,
    start_time TIME,
    end_time TIME,
    signed_in_at TIMESTAMPTZ,
    signed_out_at TIMESTAMPTZ,
    can_collect BOOLEAN,
    -- When this person can sign the child in and out here (NULLs: any
    -- time today).
    signing_opens_at TIMESTAMPTZ,
    signing_closes_at TIMESTAMPTZ
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT
        b.id,
        cp.first_name::text,
        left(cp.last_name, 1),
        st.name::text,
        lsc.start_time,
        lsc.end_time,
        ar.signed_in_at,
        ar.signed_out_at,
        p.staff_approved_at IS NOT NULL,
        w.opens_at,
        w.closes_at
    FROM public.authorized_pickup_persons p
    JOIN public.bookings b
        ON b.user_id = p.user_id
       AND b.location_id = p.location_id
    JOIN public.location_service_days d
        ON d.id = b.location_service_day_id
    JOIN public.location_services ls
        ON ls.id = d.location_service_id
    JOIN public.service_types st
        ON st.id = ls.service_type_id
    JOIN public.location_service_config lsc
        ON lsc.location_service_id = ls.id
    JOIN public.child_profile cp
        ON cp.id = b.child_id
    JOIN tenancy.locations l
        ON l.id = b.location_id
    LEFT JOIN public.attendance_records ar
        ON ar.booking_id = b.id
    CROSS JOIN LATERAL public.booking_signing_window(b.id) w
    WHERE p.id = p_pickup_person_id
      AND p.location_id = p_location_id
      AND p.is_active
      AND b.booking_status = 'CONFIRMED'
      AND d.service_date = (now() AT TIME ZONE l.timezone)::date
    ORDER BY lsc.start_time, cp.first_name, b.id;
$$;

-- A pickup person signing one of today's sessions in or out at the kiosk.
-- Only bookings kiosk_family_today shows them; signing out needs the child
-- signed in first (if not, staff should check: the child may not be here)
-- and the person approved (trg_attendance_records_rules). Signing in twice
-- changes nothing.
CREATE FUNCTION public.kiosk_sign(
    p_location_id UUID,
    p_device_id UUID,
    p_pickup_person_id UUID,
    p_booking_id UUID,
    p_action TEXT
)
RETURNS TABLE (signed_in_at TIMESTAMPTZ, signed_out_at TIMESTAMPTZ)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM public.location_kiosk_devices d
        WHERE d.id = p_device_id
          AND d.location_id = p_location_id
          AND d.kind = 'family'
          AND d.is_active
    ) OR NOT EXISTS (
        SELECT 1
        FROM public.kiosk_family_today(p_location_id, p_pickup_person_id) t
        WHERE t.booking_id = p_booking_id
    ) THEN
        RAISE EXCEPTION 'Booking % is not one of today''s for this person', p_booking_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_attendance_records_kiosk_booking',
                  TABLE = 'attendance_records',
                  SCHEMA = 'public';
    END IF;

    IF p_action = 'in' THEN
        INSERT INTO public.attendance_records (
            booking_id, signed_in_at, signed_in_by_pickup_person_id, signed_in_kiosk_device_id
        )
        VALUES (p_booking_id, now(), p_pickup_person_id, p_device_id)
        ON CONFLICT (booking_id) DO NOTHING;

    ELSIF p_action = 'out' THEN
        UPDATE public.attendance_records ar
        SET signed_out_at = now(),
            signed_out_kiosk_device_id = p_device_id,
            collected_by_pickup_person_id = p_pickup_person_id
        WHERE ar.booking_id = p_booking_id
          AND ar.signed_in_at IS NOT NULL
          AND ar.signed_out_at IS NULL;

        IF NOT FOUND AND NOT EXISTS (
            SELECT 1
            FROM public.attendance_records ar
            WHERE ar.booking_id = p_booking_id
              AND ar.signed_out_at IS NOT NULL
        ) THEN
            RAISE EXCEPTION 'Booking % has not been signed in', p_booking_id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_attendance_records_not_signed_in',
                      TABLE = 'attendance_records',
                      SCHEMA = 'public';
        END IF;

    ELSE
        RAISE EXCEPTION 'Unknown kiosk action %', p_action
            USING ERRCODE = 'invalid_parameter_value';
    END IF;

    RETURN QUERY
        SELECT ar.signed_in_at, ar.signed_out_at
        FROM public.attendance_records ar
        WHERE ar.booking_id = p_booking_id;
END;
$$;


-- =====================================================
-- ACTIONS
-- =====================================================

-- Messages from the centre to a family, shown in their account (/actions)
-- and marked read there (cited_at). Written by the system (e.g. a medical
-- review's "documents needed") or by admins on the website (slice 4-5,
-- actions c), who can withdraw one until it's read (actions d,
-- trg_actions_rules). Their email only says there's a message: the text
-- stays in the app (docs/email-policy.md).
CREATE TABLE public.actions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,
    child_id UUID,

    -- The account page the message is about (an account or child tab, e.g.
    -- "manage-documents"); NULL for a plain message.
    target TEXT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,

    -- The writer, from the session when there is one (trg_actions_rules).
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
        REFERENCES auth.users (id),

    CONSTRAINT ck_actions_text
        CHECK (btrim(title) <> '' AND btrim(message) <> '')
);

CREATE INDEX ix_actions_family
    ON public.actions (user_id, location_id, created_at DESC);

-- The writer is whoever is logged in, and a message can be withdrawn
-- (deleted) only while the family hasn't read it. Deletes cascading from
-- a removed account or child aren't withdrawals (pg_trigger_depth() > 1),
-- and server code with no session is trusted.
CREATE FUNCTION public.enforce_action_rules()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.created_by_user_id := COALESCE(auth.current_user_id(), NEW.created_by_user_id);
        NEW.created_at := now();

        RETURN NEW;
    END IF;

    IF auth.current_user_id() IS NOT NULL
       AND pg_trigger_depth() = 1
       AND OLD.cited_at IS NOT NULL THEN
        RAISE EXCEPTION 'The family has already read this message'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_actions_withdraw_unread',
                  TABLE = 'actions',
                  SCHEMA = 'public';
    END IF;

    RETURN OLD;
END;
$$;

CREATE TRIGGER trg_actions_rules
    BEFORE INSERT OR DELETE ON public.actions
    FOR EACH ROW EXECUTE FUNCTION public.enforce_action_rules();


-- =====================================================
-- STAFF SHIFTS
-- =====================================================

-- A staff member's shift at a location, started and ended at the staff
-- kiosk. One open shift per person per location. Written only by the staff
-- member themselves on the kiosk channel (schema/0005), which records the
-- device (trg_staff_shifts_device); staff see their own, admins their
-- location's.
CREATE TABLE public.staff_shifts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,
    user_id UUID NOT NULL,

    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_kiosk_device_id UUID NOT NULL,
    ended_at TIMESTAMPTZ,
    ended_kiosk_device_id UUID,

    CONSTRAINT fk_staff_shifts_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_staff_shifts_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_staff_shifts_started_kiosk
        FOREIGN KEY (started_kiosk_device_id)
        REFERENCES public.location_kiosk_devices (id),

    CONSTRAINT fk_staff_shifts_ended_kiosk
        FOREIGN KEY (ended_kiosk_device_id)
        REFERENCES public.location_kiosk_devices (id),

    CONSTRAINT ck_staff_shifts_ended_after_started
        CHECK (ended_at IS NULL OR ended_at >= started_at),

    CONSTRAINT ck_staff_shifts_ended_by
        CHECK ((ended_at IS NULL) = (ended_kiosk_device_id IS NULL))
);

CREATE UNIQUE INDEX uq_staff_shifts_open
    ON public.staff_shifts (location_id, user_id)
    WHERE ended_at IS NULL;

-- The kiosk a shift was started or ended at is the request's.
CREATE FUNCTION public.set_staff_shift_device()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        NEW.started_kiosk_device_id := COALESCE(auth.current_kiosk_device_id(), NEW.started_kiosk_device_id);
    ELSIF NEW.ended_at IS NOT NULL AND OLD.ended_at IS NULL THEN
        NEW.ended_kiosk_device_id := COALESCE(auth.current_kiosk_device_id(), NEW.ended_kiosk_device_id);
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_staff_shifts_device
    BEFORE INSERT OR UPDATE ON public.staff_shifts
    FOR EACH ROW EXECUTE FUNCTION public.set_staff_shift_device();

-- Whether someone is on shift at a location: an open shift that started on
-- the location's today. A shift left open from an earlier day (a forgotten
-- clock-out) doesn't count; it's closed with the time they left when they
-- next clock in. Only people on shift can act at the staff kiosk: the API
-- checks it for every PIN action except clocking in or out, and the
-- attendance and pickup ID triggers check it for the writes.
CREATE FUNCTION public.staff_on_shift(p_location_id UUID, p_user_id UUID)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM public.staff_shifts s
        JOIN tenancy.locations l
            ON l.id = s.location_id
        WHERE s.location_id = p_location_id
          AND s.user_id = p_user_id
          AND s.ended_at IS NULL
          AND (s.started_at AT TIME ZONE l.timezone)::date = (now() AT TIME ZONE l.timezone)::date
    );
$$;

-- "Sam L." (or "Pat L." from a typed "Pat Lee"): how the staff kiosk names
-- people before anyone enters a PIN.
CREATE FUNCTION public.short_name(p_first_name TEXT, p_last_name TEXT)
RETURNS text
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT btrim(btrim(p_first_name) || COALESCE(' ' || NULLIF(left(btrim(p_last_name), 1), '') || '.', ''));
$$;

-- "Sam L." for a staff member (staff, admin or superadmin) at the session's
-- location, e.g. who printed a plan. Staff can't read each other's user
-- rows, so this gives only the short name, only for colleagues.
CREATE FUNCTION public.staff_short_name(p_user_id UUID)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT public.short_name(u.first_name, u.last_name)
    FROM auth.users u
    WHERE u.id = p_user_id
      AND EXISTS (
          SELECT 1
          FROM auth.location_user_roles lur
          JOIN auth.roles r
              ON r.id = lur.role_id
          WHERE lur.user_id = u.id
            AND lur.location_id = NULLIF(current_setting('app.location_id', true), '')::uuid
            AND r.code IN ('staff', 'admin', 'superadmin')
      );
$$;


-- =====================================================
-- STAFF KIOSK
-- =====================================================
-- The staff kiosk is a paired tablet like the family kiosk, and nobody is
-- ever logged in to it (docs/portals.md). These functions cover what the
-- tablet needs before anyone is identified: the staff list, checking a
-- PIN, and the run sheet without personal details. Every action is a
-- separate request carrying the staff member and their PIN; once checked,
-- the API runs it as them on the kiosk channel through the normal services,
-- so RLS and the triggers above apply.

-- A staff member (staff, admin or superadmin) at the location.
CREATE FUNCTION public.is_staff_at(p_location_id UUID, p_user_id UUID)
RETURNS BOOLEAN
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.location_user_roles lur
        JOIN auth.roles r
            ON r.id = lur.role_id
        JOIN auth.users u
            ON u.id = lur.user_id
        WHERE lur.location_id = p_location_id
          AND lur.user_id = p_user_id
          AND r.code IN ('staff', 'admin', 'superadmin')
    );
$$;

-- Refuse unless the device is this location's active staff kiosk and (if
-- given) the user is staff here.
CREATE FUNCTION public.assert_staff_kiosk(p_location_id UUID, p_device_id UUID, p_staff_user_id UUID DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM public.location_kiosk_devices d
        WHERE d.id = p_device_id
          AND d.location_id = p_location_id
          AND d.kind = 'staff'
          AND d.is_active
    ) OR (
        p_staff_user_id IS NOT NULL
        AND NOT public.is_staff_at(p_location_id, p_staff_user_id)
    ) THEN
        RAISE EXCEPTION 'Not the staff kiosk, or not staff here'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_staff_kiosk_access',
                  TABLE = 'location_kiosk_devices',
                  SCHEMA = 'public';
    END IF;
END;
$$;

-- Set or change the logged-in staff member's PIN (from the website; the
-- API checks their password first). 4 digits. Clears a lock.
CREATE FUNCTION public.set_staff_pin(p_pin TEXT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_user_id UUID := auth.current_user_id();
BEGIN
    IF v_user_id IS NULL OR NOT EXISTS (
        SELECT 1
        FROM auth.location_user_roles lur
        JOIN auth.roles r
            ON r.id = lur.role_id
        WHERE lur.user_id = v_user_id
          AND r.code IN ('staff', 'admin', 'superadmin')
    ) THEN
        RAISE EXCEPTION 'Only staff have a staff PIN'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_staff_pins_staff_only',
                  TABLE = 'staff_pins',
                  SCHEMA = 'auth';
    END IF;

    IF p_pin IS NULL OR p_pin !~ '^\d{4}$' THEN
        RAISE EXCEPTION 'A PIN is 4 digits'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_staff_pins_pin_format',
                  TABLE = 'staff_pins',
                  SCHEMA = 'auth';
    END IF;

    INSERT INTO auth.staff_pins (user_id, pin_hash)
    VALUES (v_user_id, crypt(p_pin, gen_salt('bf')))
    ON CONFLICT (user_id) DO UPDATE
    SET pin_hash = EXCLUDED.pin_hash,
        failed_pin_attempts = 0,
        pin_locked_at = NULL,
        set_at = now();
END;
$$;

-- The staff a staff kiosk offers to log in as: everyone with a staff
-- role at the location, whether they've set a PIN, and whether they're on
-- shift.
CREATE FUNCTION public.staff_kiosk_staff(p_location_id UUID, p_device_id UUID)
RETURNS TABLE (
    user_id UUID,
    first_name TEXT,
    last_name TEXT,
    is_admin BOOLEAN,
    has_pin BOOLEAN,
    on_shift BOOLEAN,
    -- Today's open shift.
    shift_started_at TIMESTAMPTZ,
    -- A shift left open from an earlier day (they forgot to clock out).
    unclosed_shift_started_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    PERFORM public.assert_staff_kiosk(p_location_id, p_device_id);

    RETURN QUERY
        SELECT
            u.id,
            u.first_name::text,
            u.last_name::text,
            bool_or(r.code IN ('admin', 'superadmin')),
            bool_or(sp.user_id IS NOT NULL),
            public.staff_on_shift(p_location_id, u.id),
            CASE WHEN public.staff_on_shift(p_location_id, u.id) THEN open_shift.started_at END,
            CASE WHEN NOT public.staff_on_shift(p_location_id, u.id) THEN open_shift.started_at END
        FROM auth.location_user_roles lur
        JOIN auth.roles r
            ON r.id = lur.role_id
        JOIN auth.users u
            ON u.id = lur.user_id
        LEFT JOIN auth.staff_pins sp
            ON sp.user_id = u.id
        -- At most one (uq_staff_shifts_open).
        LEFT JOIN public.staff_shifts open_shift
            ON open_shift.location_id = p_location_id
           AND open_shift.user_id = u.id
           AND open_shift.ended_at IS NULL
        WHERE lur.location_id = p_location_id
          AND r.code IN ('staff', 'admin', 'superadmin')
        GROUP BY u.id, u.first_name, u.last_name, open_shift.started_at
        ORDER BY 2, 3;
END;
$$;

-- A staff member's PIN for one staff kiosk request.
--   ok        it's them
--   invalid   wrong PIN
--   locked    5 wrong PINs in a row; set a new PIN on the website
--   no_pin    they haven't set one yet (on the website)
CREATE FUNCTION public.staff_kiosk_verify_pin(p_location_id UUID, p_device_id UUID, p_user_id UUID, p_pin TEXT)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_pin auth.staff_pins%ROWTYPE;
    v_failures SMALLINT;
BEGIN
    PERFORM public.assert_staff_kiosk(p_location_id, p_device_id, p_user_id);

    SELECT *
    INTO v_pin
    FROM auth.staff_pins sp
    WHERE sp.user_id = p_user_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RETURN 'no_pin';
    END IF;

    IF v_pin.pin_locked_at IS NOT NULL THEN
        RETURN 'locked';
    END IF;

    IF crypt(p_pin, v_pin.pin_hash) <> v_pin.pin_hash THEN
        v_failures := v_pin.failed_pin_attempts + 1;

        UPDATE auth.staff_pins
        SET failed_pin_attempts = v_failures,
            pin_locked_at = CASE WHEN v_failures >= 5 THEN now() END
        WHERE staff_pins.user_id = p_user_id;

        RETURN CASE WHEN v_failures >= 5 THEN 'locked' ELSE 'invalid' END;
    END IF;

    UPDATE auth.staff_pins
    SET failed_pin_attempts = 0
    WHERE staff_pins.user_id = p_user_id;

    RETURN 'ok';
END;
$$;

-- A location's roll for a day: every confirmed booking, with where it's
-- up to, who did it, and whether the child is late being collected (still
-- signed in after the session ended). Shared by the staff kiosk and the
-- admin run sheet. With no user session it's the API acting for a checked
-- kiosk; with one, only admins of this location (any channel) or staff at
-- its staff kiosk (the kiosk channel) get rows (docs/portals.md). auth.*
-- helpers aren't defined yet in this file, so the session settings are read
-- directly.
CREATE FUNCTION public.attendance_roll(p_location_id UUID, p_date DATE)
RETURNS TABLE (
    booking_id UUID,
    child_id UUID,
    child_first_name TEXT,
    child_last_name TEXT,
    family_user_id UUID,
    family_first_name TEXT,
    family_last_name TEXT,
    family_phone TEXT,
    service_name TEXT,
    start_time TIME,
    end_time TIME,
    signed_in_at TIMESTAMPTZ,
    signed_in_by TEXT,
    signed_out_at TIMESTAMPTZ,
    signed_out_by TEXT,
    collected_by TEXT,
    collector_id_sighted BOOLEAN,
    released_to_name TEXT,
    release_note TEXT,
    sent_to_school BOOLEAN,
    is_late BOOLEAN,
    -- The family's emergency contact (for staff with a PIN).
    emergency_contact_name TEXT,
    emergency_contact_phone TEXT,
    emergency_contact_relation TEXT,
    emergency_contact_relation_other TEXT
)
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT
        b.id,
        cp.id,
        cp.first_name::text,
        cp.last_name::text,
        fu.id,
        fu.first_name::text,
        fu.last_name::text,
        cpr.phone::text,
        st.name::text,
        lsc.start_time,
        lsc.end_time,
        ar.signed_in_at,
        COALESCE(
            si_staff.first_name || ' ' || si_staff.last_name,
            si_person.first_name || ' ' || si_person.last_name
        ),
        ar.signed_out_at,
        so_staff.first_name || ' ' || so_staff.last_name,
        collector.first_name || ' ' || collector.last_name,
        -- Whether the collector's photo ID had been sighted by then (a later
        -- check doesn't change what happened at this sign-out).
        CASE
            WHEN collector.id IS NOT NULL THEN
                collector.identity_verified_at IS NOT NULL
                AND collector.identity_verified_at <= ar.signed_out_at
        END,
        ar.released_to_name::text,
        ar.release_note,
        COALESCE(ar.sent_to_school, FALSE),
        ar.signed_in_at IS NOT NULL
            AND ar.signed_out_at IS NULL
            AND now() > ((d.service_date + lsc.end_time) AT TIME ZONE l.timezone),
        cpr.emergency_contact_name::text,
        cpr.emergency_contact_phone::text,
        cpr.emergency_contact_relation::text,
        cpr.emergency_contact_relation_other::text
    FROM public.bookings b
    JOIN public.location_service_days d
        ON d.id = b.location_service_day_id
    JOIN public.location_services ls
        ON ls.id = d.location_service_id
    JOIN public.service_types st
        ON st.id = ls.service_type_id
    JOIN public.location_service_config lsc
        ON lsc.location_service_id = ls.id
    JOIN public.child_profile cp
        ON cp.id = b.child_id
    JOIN auth.users fu
        ON fu.id = b.user_id
    LEFT JOIN public.customer_profile cpr
        ON cpr.user_id = b.user_id
    JOIN tenancy.locations l
        ON l.id = b.location_id
    LEFT JOIN public.attendance_records ar
        ON ar.booking_id = b.id
    LEFT JOIN auth.users si_staff
        ON si_staff.id = ar.signed_in_by_user_id
    LEFT JOIN public.authorized_pickup_persons si_person
        ON si_person.id = ar.signed_in_by_pickup_person_id
    LEFT JOIN auth.users so_staff
        ON so_staff.id = ar.signed_out_by_user_id
    LEFT JOIN public.authorized_pickup_persons collector
        ON collector.id = ar.collected_by_pickup_person_id
    WHERE b.location_id = p_location_id
      AND b.booking_status = 'CONFIRMED'
      AND d.service_date = p_date
      AND (
          NULLIF(current_setting('app.user_id', true), '') IS NULL
          OR (
              p_location_id = NULLIF(current_setting('app.location_id', true), '')::uuid
              AND EXISTS (
                  SELECT 1
                  FROM auth.location_user_roles lur
                  JOIN auth.roles r
                      ON r.id = lur.role_id
                  WHERE lur.user_id = NULLIF(current_setting('app.user_id', true), '')::uuid
                    AND lur.location_id = p_location_id
                    AND (
                        r.code IN ('admin', 'superadmin')
                        OR (r.code = 'staff' AND current_setting('app.channel', true) = 'kiosk')
                    )
              )
          )
      )
    ORDER BY lsc.start_time, st.name, cp.first_name, cp.last_name, b.id;
$$;

-- What the staff kiosk shows before anyone enters a PIN (docs/portals.md,
-- section 1.3): the day's children by name, their session and where they're
-- up to, and a medical marker without details. Family contacts, pickup
-- lists, medical details and documents need a staff member's PIN (they're
-- read through the normal services, on the kiosk channel).
-- The run sheet's rows, shared by the staff kiosk (before anyone enters a
-- PIN: staff_kiosk_board) and the admin run sheet on the website. Its rows
-- come from attendance_roll, which decides who gets any: the kiosk (no
-- user session), admins on the website, staff only at the kiosk.
CREATE FUNCTION public.run_sheet_board(p_location_id UUID, p_date DATE)
RETURNS TABLE (
    booking_id UUID,
    child_id UUID,
    child_first_name TEXT,
    child_last_name TEXT,
    family_user_id UUID,
    service_name TEXT,
    start_time TIME,
    end_time TIME,
    signed_in_at TIMESTAMPTZ,
    -- Who, as "Sam L." (a staff member, or someone on the family's list).
    signed_in_by TEXT,
    signed_out_at TIMESTAMPTZ,
    -- Who took the child, as "Gran T.", and whether their ID had been
    -- sighted; or the one-off release's person.
    collected_by TEXT,
    collector_id_sighted BOOLEAN,
    released_to TEXT,
    sent_to_school BOOLEAN,
    is_late BOOLEAN,
    has_medical BOOLEAN,
    medical_review_status TEXT,
    -- Staff have written notes about the child (read at the kiosk).
    has_notes BOOLEAN
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN QUERY
        SELECT
            r.booking_id,
            r.child_id,
            r.child_first_name,
            r.child_last_name,
            r.family_user_id,
            r.service_name,
            r.start_time,
            r.end_time,
            r.signed_in_at,
            COALESCE(
                public.short_name(si_staff.first_name, si_staff.last_name),
                public.short_name(si_person.first_name, si_person.last_name)
            ),
            r.signed_out_at,
            public.short_name(collector.first_name, collector.last_name),
            r.collector_id_sighted,
            public.short_name(
                split_part(btrim(ar.released_to_name), ' ', 1),
                regexp_replace(btrim(ar.released_to_name), '^\S+\s*', '')
            ),
            r.sent_to_school,
            r.is_late,
            NULLIF(btrim(cp.medical_info), '') IS NOT NULL
                OR NULLIF(btrim(cp.allergy_info), '') IS NOT NULL
                OR NULLIF(btrim(cp.medication_info), '') IS NOT NULL
                OR EXISTS (
                    SELECT 1
                    FROM public.child_documents doc
                    WHERE doc.child_id = cp.id
                      AND doc.is_active
                      AND doc.upload_status = 'uploaded'
                ),
            ms.review_status::text,
            EXISTS (SELECT 1 FROM public.child_notes n WHERE n.child_id = cp.id)
        FROM public.attendance_roll(p_location_id, p_date) r
        JOIN public.child_profile cp
            ON cp.id = r.child_id
        LEFT JOIN public.child_medical_state ms
            ON ms.child_id = cp.id
        LEFT JOIN public.attendance_records ar
            ON ar.booking_id = r.booking_id
        LEFT JOIN auth.users si_staff
            ON si_staff.id = ar.signed_in_by_user_id
        LEFT JOIN public.authorized_pickup_persons si_person
            ON si_person.id = ar.signed_in_by_pickup_person_id
        LEFT JOIN public.authorized_pickup_persons collector
            ON collector.id = ar.collected_by_pickup_person_id;
END;
$$;

CREATE FUNCTION public.staff_kiosk_board(p_location_id UUID, p_device_id UUID, p_date DATE)
RETURNS TABLE (
    booking_id UUID,
    child_id UUID,
    child_first_name TEXT,
    child_last_name TEXT,
    family_user_id UUID,
    service_name TEXT,
    start_time TIME,
    end_time TIME,
    signed_in_at TIMESTAMPTZ,
    -- Who, as "Sam L." (a staff member, or someone on the family's list).
    signed_in_by TEXT,
    signed_out_at TIMESTAMPTZ,
    -- Who took the child, as "Gran T.", and whether their ID had been
    -- sighted; or the one-off release's person.
    collected_by TEXT,
    collector_id_sighted BOOLEAN,
    released_to TEXT,
    sent_to_school BOOLEAN,
    is_late BOOLEAN,
    has_medical BOOLEAN,
    medical_review_status TEXT,
    -- Staff have written notes about the child (read at the kiosk).
    has_notes BOOLEAN
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    PERFORM public.assert_staff_kiosk(p_location_id, p_device_id);

    RETURN QUERY SELECT * FROM public.run_sheet_board(p_location_id, p_date);
END;
$$;

-- The day's sessions on the staff kiosk's run sheet, one per service day
-- (its own tab), with places: capacity, places left (the booking rules'
-- count, service_day_places_left), and the places held by bookings still
-- awaiting payment, which aren't on the run sheet. A closed day is listed
-- only while it still has bookings. No personal details, so no PIN.
-- plpgsql: service_day_places_left is in schema/0009.
-- The day's sessions and places, shared by the staff kiosk
-- (staff_kiosk_sessions) and the admin run sheet. No personal details.
CREATE FUNCTION public.run_sheet_sessions(p_location_id UUID, p_date DATE)
RETURNS TABLE (
    location_service_day_id UUID,
    service_code TEXT,
    service_name TEXT,
    start_time TIME,
    end_time TIME,
    is_open BOOLEAN,
    capacity INTEGER,
    booked INTEGER,
    places_left INTEGER,
    awaiting_payment INTEGER,
    -- When signing in and out opens and closes (NULLs: no limit).
    signing_opens_at TIMESTAMPTZ,
    signing_closes_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN QUERY
        SELECT
            day.id,
            day.service_code,
            day.service_name,
            day.start_time,
            day.end_time,
            day.is_open,
            day.capacity,
            day.booked,
            day.places_left,
            GREATEST(day.capacity - day.places_left - day.booked, 0),
            w.opens_at,
            w.closes_at
        FROM (
            SELECT
                d.id,
                st.code::text AS service_code,
                st.name::text AS service_name,
                lsc.start_time,
                lsc.end_time,
                d.is_open,
                d.capacity,
                (
                    SELECT count(*)::integer
                    FROM public.bookings b
                    WHERE b.location_service_day_id = d.id
                      AND b.booking_status = 'CONFIRMED'
                ) AS booked,
                public.service_day_places_left(d.id) AS places_left
            FROM public.location_service_days d
            JOIN public.location_services ls
                ON ls.id = d.location_service_id
            JOIN public.service_types st
                ON st.id = ls.service_type_id
            JOIN public.location_service_config lsc
                ON lsc.location_service_id = ls.id
            WHERE d.location_id = p_location_id
              AND d.service_date = p_date
        ) day
        CROSS JOIN LATERAL public.service_day_signing_window(day.id) w
        WHERE day.is_open OR day.booked > 0
        ORDER BY day.start_time, day.service_name;
END;
$$;

CREATE FUNCTION public.staff_kiosk_sessions(p_location_id UUID, p_device_id UUID, p_date DATE)
RETURNS TABLE (
    location_service_day_id UUID,
    service_code TEXT,
    service_name TEXT,
    start_time TIME,
    end_time TIME,
    is_open BOOLEAN,
    capacity INTEGER,
    booked INTEGER,
    places_left INTEGER,
    awaiting_payment INTEGER,
    -- When signing in and out opens and closes (NULLs: no limit).
    signing_opens_at TIMESTAMPTZ,
    signing_closes_at TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    PERFORM public.assert_staff_kiosk(p_location_id, p_device_id);

    RETURN QUERY SELECT * FROM public.run_sheet_sessions(p_location_id, p_date);
END;
$$;

-- =====================================================
-- STAFF ACCOUNTS
-- =====================================================
-- Admin › Staff (slice 4-3). Who may do what is the permissions'
-- (staff_accounts, staff_admin_roles); these keep a location safe whoever
-- does it. Superadmins are set up with the tenant (slice 5), not here.

-- Staff roles at a location, from a user session:
--   * a superadmin role is never added, changed or removed here, except the
--     tenant owner's own, added for them at each location
--     (auth.grant_owner_superadmin)
--   * nobody removes or changes their own staff role (no locking yourself out)
--   * a location always keeps at least one admin or superadmin
-- Customer roles (families joining a centre) aren't affected. Writes with
-- no user session are trusted server code (seeds, tests).
CREATE FUNCTION auth.enforce_staff_role_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_old_role TEXT;
    v_new_role TEXT;
    v_location_id UUID := CASE WHEN TG_OP = 'INSERT' THEN NEW.location_id ELSE OLD.location_id END;
BEGIN
    IF auth.current_user_id() IS NULL THEN
        RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
    END IF;

    IF TG_OP <> 'INSERT' THEN
        SELECT code INTO v_old_role FROM auth.roles WHERE id = OLD.role_id;
    END IF;

    IF TG_OP <> 'DELETE' THEN
        SELECT code INTO v_new_role FROM auth.roles WHERE id = NEW.role_id;
    END IF;

    -- The one exception: the tenant's owner made superadmin at a location
    -- (auth.grant_owner_superadmin, when they add one).
    IF TG_OP = 'INSERT'
       AND v_new_role = 'superadmin'
       AND EXISTS (
           SELECT 1
           FROM auth.tenant_owners o
           JOIN tenancy.locations l
               ON l.tenant_id = o.tenant_id
           WHERE o.user_id = NEW.user_id
             AND l.id = NEW.location_id
       ) THEN
        RETURN NEW;
    END IF;

    IF 'superadmin' IN (COALESCE(v_old_role, ''), COALESCE(v_new_role, '')) THEN
        RAISE EXCEPTION 'Superadmins are set up with the tenant'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_user_roles_superadmin',
                  TABLE = 'location_user_roles',
                  SCHEMA = 'auth';
    END IF;

    IF TG_OP <> 'INSERT'
       AND v_old_role IN ('staff', 'admin')
       AND OLD.user_id = auth.current_user_id() THEN
        RAISE EXCEPTION 'You can''t change your own role'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_user_roles_self',
                  TABLE = 'location_user_roles',
                  SCHEMA = 'auth';
    END IF;

    IF TG_OP <> 'INSERT'
       AND v_old_role = 'admin'
       AND COALESCE(v_new_role, '') <> 'admin'
       AND NOT EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           JOIN auth.roles r
               ON r.id = lur.role_id
           WHERE lur.location_id = v_location_id
             AND lur.id <> OLD.id
             AND r.code IN ('admin', 'superadmin')
       ) THEN
        RAISE EXCEPTION 'Location % would have no admin', v_location_id
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_user_roles_last_admin',
                  TABLE = 'location_user_roles',
                  SCHEMA = 'auth';
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$$;

CREATE TRIGGER trg_location_user_roles_staff_rules
    BEFORE INSERT OR UPDATE OR DELETE ON auth.location_user_roles
    FOR EACH ROW EXECUTE FUNCTION auth.enforce_staff_role_rules();

-- Whether the session user can manage this location's staff accounts, and
-- the target is a staff member or admin there (never a superadmin). The
-- functions below act past RLS (admins can't read each other's accounts or
-- PINs), so they check this first. plpgsql: auth.is_location_admin is in
-- schema/0005.
CREATE FUNCTION public.can_manage_location_staff(p_location_id UUID, p_user_id UUID)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN auth.is_location_admin(p_location_id)
       AND EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           JOIN auth.roles r
               ON r.id = lur.role_id
           WHERE lur.location_id = p_location_id
             AND lur.user_id = p_user_id
             AND r.code IN ('staff', 'admin')
       )
       AND NOT EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           JOIN auth.roles r
               ON r.id = lur.role_id
           WHERE lur.location_id = p_location_id
             AND lur.user_id = p_user_id
             AND r.code = 'superadmin'
       );
END;
$$;

-- Everyone who works at the location, for its admins: their role, whether
-- they've set a staff PIN, and when they last logged in (NULL: invited,
-- not yet logged in). plpgsql: auth.is_location_admin is in schema/0005.
CREATE FUNCTION public.location_staff(p_location_id UUID)
RETURNS TABLE (
    user_id UUID,
    first_name TEXT,
    last_name TEXT,
    email TEXT,
    role_code TEXT,
    has_pin BOOLEAN,
    last_login TIMESTAMPTZ
)
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    RETURN QUERY
    SELECT
        u.id,
        u.first_name::text,
        u.last_name::text,
        u.email::text,
        -- One staff role each; the highest if there were ever two.
        (array_agg(r.code ORDER BY CASE r.code WHEN 'superadmin' THEN 0 WHEN 'admin' THEN 1 ELSE 2 END))[1]::text,
        bool_or(sp.user_id IS NOT NULL),
        u.last_login
    FROM auth.location_user_roles lur
    JOIN auth.roles r
        ON r.id = lur.role_id
    JOIN auth.users u
        ON u.id = lur.user_id
    LEFT JOIN auth.staff_pins sp
        ON sp.user_id = u.id
    WHERE lur.location_id = p_location_id
      AND r.code IN ('staff', 'admin', 'superadmin')
      AND auth.is_location_admin(p_location_id)
    GROUP BY u.id, u.first_name, u.last_name, u.email, u.last_login
    ORDER BY u.first_name, u.last_name;
END;
$$;

-- Correct a staff member's or admin's name (staff can't change their own).
CREATE FUNCTION public.set_staff_name(p_location_id UUID, p_user_id UUID, p_first_name TEXT, p_last_name TEXT)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT public.can_manage_location_staff(p_location_id, p_user_id) THEN
        RAISE EXCEPTION 'Not a staff member here'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_staff_managed',
                  TABLE = 'users',
                  SCHEMA = 'auth';
    END IF;

    UPDATE auth.users
    SET first_name = COALESCE(NULLIF(btrim(p_first_name), ''), first_name),
        last_name = COALESCE(NULLIF(btrim(p_last_name), ''), last_name)
    WHERE id = p_user_id;
END;
$$;

-- Clear a staff member's kiosk PIN (e.g. it's been shared): they set a new
-- one on their account page.
CREATE FUNCTION public.reset_staff_pin(p_location_id UUID, p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT public.can_manage_location_staff(p_location_id, p_user_id) THEN
        RAISE EXCEPTION 'Not a staff member here'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_staff_managed',
                  TABLE = 'staff_pins',
                  SCHEMA = 'auth';
    END IF;

    DELETE FROM auth.staff_pins WHERE user_id = p_user_id;
END;
$$;

-- Remove someone from the location's staff: their staff role goes (the
-- role rules above still apply), and an open shift is closed now, recorded
-- against the kiosk it started on. Their account and records stay.
CREATE FUNCTION public.remove_location_staff(p_location_id UUID, p_user_id UUID)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT public.can_manage_location_staff(p_location_id, p_user_id) THEN
        RAISE EXCEPTION 'Not a staff member here'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_location_staff_managed',
                  TABLE = 'location_user_roles',
                  SCHEMA = 'auth';
    END IF;

    DELETE FROM auth.location_user_roles lur
    USING auth.roles r
    WHERE r.id = lur.role_id
      AND lur.location_id = p_location_id
      AND lur.user_id = p_user_id
      AND r.code IN ('staff', 'admin');

    UPDATE public.staff_shifts
    SET ended_at = now(),
        ended_kiosk_device_id = started_kiosk_device_id
    WHERE location_id = p_location_id
      AND user_id = p_user_id
      AND ended_at IS NULL;
END;
$$;


-- =====================================================
-- EMAIL MESSAGES
-- =====================================================

-- One row per email sent (docs/email-policy.md, section 6): what was sent,
-- to whom (by reference, plus a masked address for support), and what
-- happened to it. Never the body, the template variables or the full
-- address. Written only by the email service (app/integrations/email),
-- which sets app.email_writer (schema/0005); location admins can read
-- their location's rows.
--
-- After 2 years the recipient is cleared (recipient_cleared_at) and the
-- row kept for usage counts (reporting.email_usage_monthly).
CREATE TABLE public.email_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Set from the location by trg_email_messages_tenant.
    tenant_id UUID NOT NULL,
    location_id UUID NOT NULL,

    email_type public.email_type_enum NOT NULL,

    -- Who it went to: a user, or a pickup person (kiosk PINs). The masked
    -- address ("j***@gmail.com") is enough for support to recognise it.
    recipient_user_id UUID,
    recipient_pickup_person_id UUID,
    recipient_masked VARCHAR(255),
    recipient_cleared_at TIMESTAMPTZ,

    status public.email_status_enum NOT NULL DEFAULT 'queued',
    -- The provider's message id (SES MessageId): how bounce, complaint and
    -- delivery events find the row.
    provider_message_id VARCHAR(255),
    -- A provider or app error code only. Provider messages can quote the
    -- address, so they aren't stored.
    error_code VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at TIMESTAMPTZ,
    status_updated_at TIMESTAMPTZ,

    CONSTRAINT fk_email_messages_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_email_messages_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_email_messages_recipient_user
        FOREIGN KEY (recipient_user_id)
        REFERENCES auth.users (id)
        ON DELETE SET NULL,

    CONSTRAINT fk_email_messages_recipient_pickup_person
        FOREIGN KEY (recipient_pickup_person_id)
        REFERENCES public.authorized_pickup_persons (id)
        ON DELETE SET NULL,

    CONSTRAINT uq_email_messages_provider_message
        UNIQUE (provider_message_id),

    -- One kind of recipient per email.
    CONSTRAINT ck_email_messages_one_recipient
        CHECK (recipient_user_id IS NULL OR recipient_pickup_person_id IS NULL)
);

CREATE INDEX idx_email_messages_tenant_created
    ON public.email_messages (tenant_id, created_at);

CREATE INDEX idx_email_messages_location_created
    ON public.email_messages (location_id, created_at);

CREATE FUNCTION public.set_email_message_tenant()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    SELECT l.tenant_id
    INTO NEW.tenant_id
    FROM tenancy.locations l
    WHERE l.id = NEW.location_id;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_email_messages_tenant
    BEFORE INSERT OR UPDATE OF location_id ON public.email_messages
    FOR EACH ROW EXECUTE FUNCTION public.set_email_message_tenant();


-- =====================================================
-- EMAIL TEMPLATE OVERRIDES
-- =====================================================

-- A tenant's own wording for one email type. Only the editable slots
-- (docs/email-policy.md, section 5); an empty slot uses the platform's
-- default. Plain text with whitelisted placeholders, checked by the API
-- when saved; the locked parts (links, the PIN block, the footer) can't be
-- changed. Edited from tenant configuration (not built yet).
CREATE TABLE tenancy.email_template_overrides (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id UUID NOT NULL,
    email_type public.email_type_enum NOT NULL,

    subject VARCHAR(150),
    heading VARCHAR(150),
    body TEXT,
    sign_off VARCHAR(150),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_by_user_id UUID,

    CONSTRAINT fk_email_template_overrides_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_email_template_overrides_updated_by
        FOREIGN KEY (updated_by_user_id)
        REFERENCES auth.users (id)
        ON DELETE SET NULL,

    CONSTRAINT uq_email_template_overrides_tenant_type
        UNIQUE (tenant_id, email_type),

    CONSTRAINT ck_email_template_overrides_body_length
        CHECK (body IS NULL OR char_length(body) <= 2000)
);

CREATE TRIGGER trg_email_template_overrides_updated_at
    BEFORE UPDATE ON tenancy.email_template_overrides
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- REPORTING: EMAIL USAGE
-- =====================================================

-- Emails per tenant per month (Sydney time) and type, with how many
-- failed, bounced or drew complaints. For the platform owner: the app's
-- runtime role can't read the reporting schema.
CREATE VIEW reporting.email_usage_monthly AS
SELECT
    t.id AS tenant_id,
    t.code AS tenant_code,
    date_trunc('month', m.created_at AT TIME ZONE 'Australia/Sydney')::date AS month,
    m.email_type,
    count(*) AS emails,
    count(*) FILTER (WHERE m.status = 'failed') AS failed,
    count(*) FILTER (WHERE m.status = 'bounced') AS bounced,
    count(*) FILTER (WHERE m.status = 'complained') AS complained
FROM public.email_messages m
JOIN tenancy.tenants t
    ON t.id = m.tenant_id
GROUP BY t.id, t.code, 3, m.email_type;
