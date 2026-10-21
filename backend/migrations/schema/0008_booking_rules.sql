-- Booking rules that depend on other tables, so they can't be CHECKs:
--
--   ck_bookings_service_day_in_future   the day is after today, in the
--                                       location's timezone
--   ck_bookings_service_day_open        the day is open
--   ck_bookings_service_day_full        the day has a place left
--   ck_bookings_child_medically_cleared the child's medical review is
--                                       approved or not required
--
-- Capacity has to live here: under RLS a customer only sees their own
-- bookings, so a count in the API can't see other families' places.
--
-- They run on INSERT only, so existing bookings (including past ones, or
-- a child who later needs review) can still change status. Each raises a
-- check_violation with its own constraint name, which
-- app/errors/database.py maps to an API error.


-- SECURITY DEFINER: reads the service day and medical state without RLS,
-- so a booking for another family's child reaches the composite foreign
-- key (and its "invalid child" error) instead of failing here on a row
-- RLS hides. The fixed search_path stops callers shadowing these tables.
CREATE FUNCTION public.enforce_booking_rules()
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
    v_review_status public.medical_review_status_enum;
BEGIN
    -- Locking the day makes concurrent bookings for it queue, so two
    -- requests can't both take the last place.
    SELECT d.service_date, d.is_open, d.capacity, l.timezone
    INTO v_service_date, v_is_open, v_capacity, v_timezone
    FROM public.location_service_days d
    JOIN tenancy.locations l
        ON l.id = d.location_id
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

        -- Every family's live bookings (this function bypasses RLS),
        -- including ones inserted earlier in this transaction.
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

    SELECT ms.review_status
    INTO v_review_status
    FROM public.child_medical_state ms
    WHERE ms.child_id = NEW.child_id;

    -- An unknown child is left to fk_bookings_child.
    IF FOUND AND v_review_status NOT IN ('approved', 'not_required') THEN
        RAISE EXCEPTION 'Child % is awaiting medical review (%)', NEW.child_id, v_review_status
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_bookings_child_medically_cleared',
                  TABLE = 'bookings',
                  SCHEMA = 'public';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_bookings_enforce_rules
    BEFORE INSERT ON public.bookings
    FOR EACH ROW EXECUTE FUNCTION public.enforce_booking_rules();
