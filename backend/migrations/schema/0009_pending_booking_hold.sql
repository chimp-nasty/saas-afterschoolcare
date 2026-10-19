-- A PENDING booking holds its place for a limited time.
--
-- Normally Stripe's checkout.session.expired webhook releases abandoned
-- bookings (sessions expire after 30 minutes). If that webhook is missed,
-- the hold still lapses here, so a dead checkout can't keep a place or
-- block the same child being rebooked:
--
--   * reads use effective_booking_status(), which reports a lapsed hold as
--     EXPIRED (home, review, lists, conflict preview)
--   * the booking trigger turns that day's lapsed holds into real EXPIRED
--     rows before counting places, so the capacity rule and the partial
--     unique index (which can't use now()) both see the right state
--
-- The hold is longer than Stripe's session so a payment made at the last
-- minute still has time for its webhook to arrive.


-- The single source of truth for how long a hold lasts.
CREATE FUNCTION public.booking_hold_lapsed(
    p_status public.booking_status_enum,
    p_created_at TIMESTAMPTZ
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT p_status = 'PENDING'
       AND p_created_at < now() - interval '60 minutes';
$$;


-- The status to show and filter on: a lapsed hold reads as EXPIRED.
CREATE FUNCTION public.effective_booking_status(
    p_status public.booking_status_enum,
    p_created_at TIMESTAMPTZ
)
RETURNS public.booking_status_enum
LANGUAGE sql
STABLE
AS $$
    SELECT CASE
        WHEN public.booking_hold_lapsed(p_status, p_created_at)
            THEN 'EXPIRED'::public.booking_status_enum
        ELSE p_status
    END;
$$;


-- Same rules as 0008, plus expiring the day's lapsed holds before
-- counting ("LAPSED HOLDS"), and checking the child is still active and
-- within the service's age range on the day ("CHILD").
CREATE OR REPLACE FUNCTION public.enforce_booking_rules()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_service_date DATE;
    v_is_open BOOLEAN;
    v_capacity INTEGER;
    v_timezone TEXT;
    v_live_bookings INTEGER;
    v_min_child_age SMALLINT;
    v_max_child_age SMALLINT;
    v_review_status public.medical_review_status_enum;
    v_dob DATE;
    v_is_active BOOLEAN;
    v_age INTEGER;
BEGIN
    -- Locking the day makes concurrent bookings for it queue, so two
    -- requests can't both take the last place.
    SELECT d.service_date, d.is_open, d.capacity, l.timezone,
           ls.min_child_age, ls.max_child_age
    INTO v_service_date, v_is_open, v_capacity, v_timezone,
         v_min_child_age, v_max_child_age
    FROM public.location_service_days d
    JOIN tenancy.locations l
        ON l.id = d.location_id
    JOIN public.location_services ls
        ON ls.id = d.location_service_id
    WHERE d.id = NEW.location_service_day_id
    FOR UPDATE OF d;

    -- An unknown day is left to fk_bookings_location_service_day.
    IF FOUND THEN
        IF v_service_date <= (now() AT TIME ZONE v_timezone)::date THEN
            RAISE EXCEPTION 'Service day % is not in the future', v_service_date
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_service_day_in_future',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;

        IF NOT v_is_open THEN
            RAISE EXCEPTION 'Service day % is closed', v_service_date
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_service_day_open',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;

        -- LAPSED HOLDS: release this day's abandoned checkouts (any family;
        -- this function bypasses RLS) before the place count and the
        -- duplicate-booking index look at them.
        UPDATE public.bookings b
        SET booking_status = 'EXPIRED',
            payment_status = 'FAILED'
        WHERE b.location_service_day_id = NEW.location_service_day_id
          AND public.booking_hold_lapsed(b.booking_status, b.created_at);

        -- Every family's live bookings, including ones inserted earlier in
        -- this transaction.
        SELECT count(*)
        INTO v_live_bookings
        FROM public.bookings b
        WHERE b.location_service_day_id = NEW.location_service_day_id
          AND b.booking_status IN ('PENDING', 'CONFIRMED');

        IF v_live_bookings >= v_capacity THEN
            RAISE EXCEPTION 'Service day % is full (capacity %)', v_service_date, v_capacity
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_service_day_full',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;
    END IF;

    -- CHILD
    SELECT cp.dob, cp.is_active, ms.review_status
    INTO v_dob, v_is_active, v_review_status
    FROM public.child_profile cp
    LEFT JOIN public.child_medical_state ms
        ON ms.child_id = cp.id
    WHERE cp.id = NEW.child_id;

    -- An unknown child is left to fk_bookings_child.
    IF FOUND THEN
        IF NOT v_is_active THEN
            RAISE EXCEPTION 'Child % has been removed', NEW.child_id
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_child_active',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;

        IF v_review_status NOT IN ('approved', 'not_required') THEN
            RAISE EXCEPTION 'Child % is awaiting medical review (%)', NEW.child_id, v_review_status
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_child_medically_cleared',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;

        -- Age in whole years on the day of the session. Skipped when the
        -- day is unknown (no service date to measure against).
        v_age := date_part('year', age(v_service_date, v_dob))::integer;

        IF v_service_date IS NOT NULL
           AND (v_age < v_min_child_age OR v_age > v_max_child_age) THEN
            RAISE EXCEPTION 'Child % is % on %, outside ages % to %',
                    NEW.child_id, v_age, v_service_date, v_min_child_age, v_max_child_age
                USING ERRCODE = 'check_violation',
                      CONSTRAINT = 'ck_bookings_child_age',
                      TABLE = 'bookings',
                      SCHEMA = 'public';
        END IF;
    END IF;

    RETURN NEW;
END;
$$;
