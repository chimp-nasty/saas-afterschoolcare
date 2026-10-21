-- Scope RLS to the session's location.
--
-- Until now a user with roles at two locations saw both locations' rows,
-- whichever site they logged into. The session's location (app.location_id,
-- set from the JWT by app/dependencies/rls.py) now has to match as well.
--
-- The helpers keep their signatures, so every policy built on them picks
-- this up without being recreated.


-- The session's location, or NULL when unset (unset means no access to
-- location-scoped rows).
CREATE FUNCTION auth.current_location_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.location_id', true), '')::uuid;
$$;


-- The request's channel (docs/portals.md, section 3): 'kiosk' when the API
-- is acting for a staff member at the location's staff kiosk (their PIN
-- checked for this request), 'web' otherwise. Set per transaction by the API.
CREATE FUNCTION auth.current_channel()
RETURNS text
LANGUAGE sql
STABLE
AS $$
    SELECT COALESCE(NULLIF(current_setting('app.channel', true), ''), 'web');
$$;


-- The staff kiosk the request came from, on the kiosk channel.
CREATE FUNCTION auth.current_kiosk_device_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.kiosk_device_id', true), '')::uuid;
$$;


-- The current user holds any role at the location, and it's the session's
-- location.
CREATE OR REPLACE FUNCTION auth.has_location_role(p_location_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT p_location_id = auth.current_location_id()
       AND EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           WHERE lur.user_id = auth.current_user_id()
             AND lur.location_id = p_location_id
       );
$$;


-- The current user is staff or above at the location, and it's the
-- session's location. The staff role only counts at the staff kiosk: on the
-- website, staff manage only themselves (docs/portals.md), so a staff login
-- reads no children, families, medical or attendance rows.
CREATE OR REPLACE FUNCTION auth.is_location_staff(p_location_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT p_location_id = auth.current_location_id()
       AND EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           JOIN auth.roles r
               ON r.id = lur.role_id
           WHERE lur.user_id = auth.current_user_id()
             AND lur.location_id = p_location_id
             AND (
                 r.code IN ('superadmin', 'admin')
                 OR (r.code = 'staff' AND auth.current_channel() = 'kiosk')
             )
       );
$$;


-- The current user is an admin or superadmin at the location, and it's the
-- session's location.
CREATE OR REPLACE FUNCTION auth.is_location_admin(p_location_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT p_location_id = auth.current_location_id()
       AND EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           JOIN auth.roles r
               ON r.id = lur.role_id
           WHERE lur.user_id = auth.current_user_id()
             AND lur.location_id = p_location_id
             AND r.code IN ('superadmin', 'admin')
       );
$$;


-- Staff and above at the row's location see every row there; customers
-- see only rows they own. Either way, only at the session's location.
CREATE OR REPLACE FUNCTION auth.can_access_location_row(
    p_location_id uuid,
    p_owner_user_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT p_location_id = auth.current_location_id()
       AND EXISTS (
           SELECT 1
           FROM auth.location_user_roles lur
           JOIN auth.roles r
               ON r.id = lur.role_id
           WHERE lur.user_id = auth.current_user_id()
             AND lur.location_id = p_location_id
             AND (
                 r.code IN ('superadmin', 'admin')
                 -- Staff only at the staff kiosk (see is_location_staff).
                 OR (r.code = 'staff' AND auth.current_channel() = 'kiosk')
                 OR (
                     r.code = 'customer'
                     AND p_owner_user_id = auth.current_user_id()
                 )
             )
       );
$$;


-- The current user outranks the target user at the session's location
-- (and at p_location_id, when given): staff > customer,
-- admin > staff/customer, superadmin > admin/staff/customer.
CREATE OR REPLACE FUNCTION auth.can_manage_user(
    p_target_user_id uuid,
    p_location_id uuid DEFAULT NULL
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.location_user_roles current_lur
        JOIN auth.roles cr
            ON cr.id = current_lur.role_id
        JOIN auth.location_user_roles target_lur
            ON target_lur.location_id = current_lur.location_id
        JOIN auth.roles tr
            ON tr.id = target_lur.role_id
        WHERE current_lur.user_id = auth.current_user_id()
          AND current_lur.location_id = auth.current_location_id()
          AND target_lur.user_id = p_target_user_id
          AND (
              p_location_id IS NULL
              OR current_lur.location_id = p_location_id
          )
          AND (
              -- Staff only at the staff kiosk (see is_location_staff).
              (cr.code = 'staff' AND tr.code = 'customer' AND auth.current_channel() = 'kiosk')
              OR (cr.code = 'admin' AND tr.code IN ('staff', 'customer'))
              OR (cr.code = 'superadmin' AND tr.code IN ('admin', 'staff', 'customer'))
          )
    );
$$;


-- booking_groups is user-owned but now has a location, so scope it too.
DROP POLICY booking_groups_scope_policy ON public.booking_groups;

CREATE POLICY booking_groups_scope_policy
    ON public.booking_groups FOR ALL
    USING (
        user_id = auth.current_user_id()
        AND location_id = auth.current_location_id()
    )
    WITH CHECK (
        user_id = auth.current_user_id()
        AND location_id = auth.current_location_id()
    );


-- Staff start and end their own shifts, only at the staff kiosk (here
-- rather than schema/0005: it needs auth.current_channel()).
CREATE POLICY staff_shifts_kiosk_write_policy
    ON public.staff_shifts FOR ALL
    USING (
        user_id = auth.current_user_id()
        AND auth.current_channel() = 'kiosk'
        AND auth.is_location_staff(location_id)
    )
    WITH CHECK (
        user_id = auth.current_user_id()
        AND auth.current_channel() = 'kiosk'
        AND auth.is_location_staff(location_id)
    );
