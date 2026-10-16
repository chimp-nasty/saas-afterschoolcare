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
                 r.code IN ('superadmin', 'admin', 'staff')
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
              (cr.code = 'staff' AND tr.code = 'customer')
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
