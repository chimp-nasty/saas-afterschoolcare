-- Row level security.
--
-- The app sets app.user_id (and app.location_id) per transaction; see
-- app/dependencies/rls.py. The helper functions below hold the shared
-- predicates so each policy reads as a single rule.


-- =====================================================
-- HELPERS
-- =====================================================

-- The current user, or NULL when unset (unset means no access rather
-- than a cast error).
CREATE FUNCTION auth.current_user_id()
RETURNS uuid
LANGUAGE sql
STABLE
AS $$
    SELECT NULLIF(current_setting('app.user_id', true), '')::uuid;
$$;

-- The current user holds any role at the location.
CREATE FUNCTION auth.has_location_role(p_location_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.location_user_roles lur
        WHERE lur.user_id = auth.current_user_id()
          AND lur.location_id = p_location_id
    );
$$;

-- The request is a platform admin's (app.platform_admin_id, set for the
-- platform's site only): an active one. SECURITY DEFINER: reads past the
-- platform_admins policies.
CREATE FUNCTION auth.is_platform_admin()
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.platform_admins a
        WHERE a.id = NULLIF(current_setting('app.platform_admin_id', true), '')::uuid
          AND a.is_active
    );
$$;

-- The request is the domain check's (app/tenancy/services/domain_check.py):
-- server code with no user, moving every business's custom domains along
-- (app.channel, set only by that service).
CREATE FUNCTION auth.is_domain_check()
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT current_setting('app.channel', true) = 'domain_check'
       AND auth.current_user_id() IS NULL;
$$;

-- The current user holds a tenant permission (docs/tenant-administration.md)
-- for the tenant: read from the grants each time, so taking one away works
-- at once, whatever the token still says.
CREATE FUNCTION auth.has_tenant_permission(
    p_tenant_id uuid,
    p_resource text,
    p_action text
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.user_tenant_permissions utp
        JOIN auth.permissions p
            ON p.id = utp.permission_id
        WHERE utp.user_id = auth.current_user_id()
          AND utp.tenant_id = p_tenant_id
          AND p.resource = p_resource
          AND p.action = p_action
    );
$$;

-- Staff and above at the row's location see every row there; customers
-- at that location see only rows they own.
CREATE FUNCTION auth.can_access_location_row(
    p_location_id uuid,
    p_owner_user_id uuid
)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
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

-- The current user is staff or above at the location (redefined in
-- schema/0007 to also require it's the session's location).
CREATE FUNCTION auth.is_location_staff(p_location_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.location_user_roles lur
        JOIN auth.roles r
            ON r.id = lur.role_id
        WHERE lur.user_id = auth.current_user_id()
          AND lur.location_id = p_location_id
          AND r.code IN ('superadmin', 'admin', 'staff')
    );
$$;

-- The current user is an admin or superadmin at the location (redefined in
-- schema/0007 to also require it's the session's location).
CREATE FUNCTION auth.is_location_admin(p_location_id uuid)
RETURNS boolean
LANGUAGE sql
STABLE
AS $$
    SELECT EXISTS (
        SELECT 1
        FROM auth.location_user_roles lur
        JOIN auth.roles r
            ON r.id = lur.role_id
        WHERE lur.user_id = auth.current_user_id()
          AND lur.location_id = p_location_id
          AND r.code IN ('superadmin', 'admin')
    );
$$;

-- The current user outranks the target user at a shared location
-- (optionally a specific one): staff > customer, admin > staff/customer,
-- superadmin > admin/staff/customer.
CREATE FUNCTION auth.can_manage_user(
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


-- =====================================================
-- TENANCY
-- =====================================================

ALTER TABLE tenancy.tenants ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenants FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.locations FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_branding ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_branding FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_faqs ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_faqs FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_highlights ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_highlights FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_stripe_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_stripe_accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_domains ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_domains FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_certificates ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.tenant_certificates FORCE ROW LEVEL SECURITY;

CREATE POLICY tenants_read_policy
    ON tenancy.tenants FOR SELECT
    USING (true);

CREATE POLICY locations_read_policy
    ON tenancy.locations FOR SELECT
    USING (true);

-- The business's site (stage 5): anyone reads it (its public pages); its
-- owner changes it. Documents are only ever added (versions).
CREATE POLICY tenant_branding_read_policy
    ON tenancy.tenant_branding FOR SELECT
    USING (true);

CREATE POLICY tenant_branding_write_policy
    ON tenancy.tenant_branding FOR ALL
    USING (auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u'))
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u'));

CREATE POLICY tenant_faqs_read_policy
    ON tenancy.tenant_faqs FOR SELECT
    USING (true);

CREATE POLICY tenant_faqs_write_policy
    ON tenancy.tenant_faqs FOR ALL
    USING (auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u'))
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u'));

CREATE POLICY tenant_highlights_read_policy
    ON tenancy.tenant_highlights FOR SELECT
    USING (true);

CREATE POLICY tenant_highlights_write_policy
    ON tenancy.tenant_highlights FOR ALL
    USING (auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u'))
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u'));

CREATE POLICY tenant_documents_read_policy
    ON tenancy.tenant_documents FOR SELECT
    USING (true);

CREATE POLICY tenant_documents_insert_policy
    ON tenancy.tenant_documents FOR INSERT
    WITH CHECK (
        auth.has_tenant_permission(tenant_id, 'tenant_settings', 'u')
        AND uploaded_by = auth.current_user_id()
    );

-- A tenant's Stripe account: read by anyone with a role at one of its
-- locations (a family's checkout needs it; admins see the status) and by
-- its owner; connected and changed by the owner (tenant_stripe_account u).
-- Stripe's webhooks update it through tenancy.sync_stripe_account.
CREATE POLICY tenant_stripe_accounts_read_policy
    ON tenancy.tenant_stripe_accounts FOR SELECT
    USING (
        EXISTS (
            SELECT 1
            FROM tenancy.locations l
            WHERE l.tenant_id = tenant_stripe_accounts.tenant_id
              AND auth.has_location_role(l.id)
        )
        OR auth.has_tenant_permission(tenant_id, 'tenant_stripe_account', 'r')
        -- The platform's tenant list shows whether each takes payments.
        OR auth.is_platform_admin()
    );

CREATE POLICY tenant_stripe_accounts_write_policy
    ON tenancy.tenant_stripe_accounts FOR ALL
    USING (auth.has_tenant_permission(tenant_id, 'tenant_stripe_account', 'u'))
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_stripe_account', 'u'));

-- The owner changes the business's details; the domain check sets its live
-- main domain (custom_domain, schema/0002). Tenants are created at
-- registration (server code), never from a user session.
CREATE POLICY tenants_update_policy
    ON tenancy.tenants FOR UPDATE
    USING (auth.has_tenant_permission(id, 'tenant_settings', 'u') OR auth.is_domain_check())
    WITH CHECK (auth.has_tenant_permission(id, 'tenant_settings', 'u') OR auth.is_domain_check());

-- Custom domains (schema/0002): the owner sees them, adds them and marks
-- them for removal (the triggers allow nothing more); the platform's list
-- shows them; the domain check sees and changes every business's.
CREATE POLICY tenant_domains_read_policy
    ON tenancy.tenant_domains FOR SELECT
    USING (
        auth.has_tenant_permission(tenant_id, 'tenant_domains', 'r')
        OR auth.is_platform_admin()
        OR auth.is_domain_check()
    );

CREATE POLICY tenant_domains_insert_policy
    ON tenancy.tenant_domains FOR INSERT
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_domains', 'u'));

CREATE POLICY tenant_domains_update_policy
    ON tenancy.tenant_domains FOR UPDATE
    USING (auth.has_tenant_permission(tenant_id, 'tenant_domains', 'u') OR auth.is_domain_check())
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_domains', 'u') OR auth.is_domain_check());

CREATE POLICY tenant_domains_delete_policy
    ON tenancy.tenant_domains FOR DELETE
    USING (auth.is_domain_check());

CREATE POLICY tenant_certificates_read_policy
    ON tenancy.tenant_certificates FOR SELECT
    USING (
        auth.has_tenant_permission(tenant_id, 'tenant_domains', 'r')
        OR auth.is_platform_admin()
        OR auth.is_domain_check()
    );

CREATE POLICY tenant_certificates_write_policy
    ON tenancy.tenant_certificates FOR ALL
    USING (auth.is_domain_check())
    WITH CHECK (auth.is_domain_check());

-- The owner adds and edits the tenant's locations.
CREATE POLICY locations_insert_policy
    ON tenancy.locations FOR INSERT
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_locations', 'c'));

CREATE POLICY locations_update_policy
    ON tenancy.locations FOR UPDATE
    USING (auth.has_tenant_permission(tenant_id, 'tenant_locations', 'u'))
    WITH CHECK (auth.has_tenant_permission(tenant_id, 'tenant_locations', 'u'));


-- =====================================================
-- AUTH
-- =====================================================

-- Platform admins (schema/0003): themselves, and by email while logging in.
ALTER TABLE auth.platform_admins ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.platform_admins FORCE ROW LEVEL SECURITY;

CREATE POLICY platform_admins_self_policy
    ON auth.platform_admins FOR SELECT
    USING (id = NULLIF(current_setting('app.platform_admin_id', true), '')::uuid);

CREATE POLICY platform_admins_login_policy
    ON auth.platform_admins FOR SELECT
    USING (email = NULLIF(current_setting('app.login_email', true), ''));

CREATE POLICY platform_admins_update_policy
    ON auth.platform_admins FOR UPDATE
    USING (id = NULLIF(current_setting('app.platform_admin_id', true), '')::uuid)
    WITH CHECK (id = NULLIF(current_setting('app.platform_admin_id', true), '')::uuid);

-- Invites are the platform's. Registration reads and uses one through
-- auth.usable_invite_email and auth.register_tenant.
ALTER TABLE auth.tenant_invites ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.tenant_invites FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_invites_platform_policy
    ON auth.tenant_invites FOR ALL
    USING (auth.is_platform_admin())
    WITH CHECK (auth.is_platform_admin());

ALTER TABLE auth.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.roles FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.permissions FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.role_permissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.role_permissions FORCE ROW LEVEL SECURITY;
ALTER TABLE auth.users ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.users FORCE ROW LEVEL SECURITY;

CREATE POLICY roles_scope_policy
    ON auth.roles FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY permissions_scope_policy
    ON auth.permissions FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY role_permissions_scope_policy
    ON auth.role_permissions FOR ALL
    USING (true) WITH CHECK (true);

-- Users see themselves and the users they outrank.
CREATE POLICY users_scope_policy
    ON auth.users FOR SELECT
    USING (
        id = auth.current_user_id()
        OR auth.can_manage_user(users.id)
    );

-- Login looks a user up by email before app.user_id is known.
CREATE POLICY users_login_policy
    ON auth.users FOR SELECT
    USING (
        email = NULLIF(current_setting('app.login_email', true), '')
    );

CREATE POLICY users_update_policy
    ON auth.users FOR UPDATE
    USING (
        id = auth.current_user_id()
        OR auth.can_manage_user(users.id)
    )
    WITH CHECK (
        id = auth.current_user_id()
        OR auth.can_manage_user(users.id)
    );

CREATE POLICY users_delete_policy
    ON auth.users FOR DELETE
    USING (
        id = auth.current_user_id()
        OR auth.can_manage_user(users.id)
    );

-- Registration.
CREATE POLICY users_insert_scope_policy
    ON auth.users FOR INSERT
    WITH CHECK (true);


-- =====================================================
-- PUBLIC
-- =====================================================

ALTER TABLE public.service_types ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.service_types FORCE ROW LEVEL SECURITY;
ALTER TABLE public.customer_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.customer_profile FORCE ROW LEVEL SECURITY;
ALTER TABLE public.booking_groups ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.booking_groups FORCE ROW LEVEL SECURITY;
ALTER TABLE public.location_services ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.location_service_config ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.location_service_config FORCE ROW LEVEL SECURITY;
ALTER TABLE public.location_services FORCE ROW LEVEL SECURITY;
ALTER TABLE public.location_service_days ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.location_service_days FORCE ROW LEVEL SECURITY;
ALTER TABLE public.location_kiosk_devices ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.location_kiosk_devices FORCE ROW LEVEL SECURITY;
ALTER TABLE public.child_profile ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.child_profile FORCE ROW LEVEL SECURITY;
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookings FORCE ROW LEVEL SECURITY;
ALTER TABLE public.payment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payment_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE public.refunds ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.refunds FORCE ROW LEVEL SECURITY;
ALTER TABLE public.child_medical_state ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.child_medical_state FORCE ROW LEVEL SECURITY;
ALTER TABLE public.actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.actions FORCE ROW LEVEL SECURITY;
ALTER TABLE public.child_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.child_notes FORCE ROW LEVEL SECURITY;
ALTER TABLE public.child_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.child_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE public.authorized_pickup_persons ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.authorized_pickup_persons FORCE ROW LEVEL SECURITY;
ALTER TABLE public.attendance_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attendance_records FORCE ROW LEVEL SECURITY;

-- Global
CREATE POLICY service_types_scope_policy
    ON public.service_types FOR ALL
    USING (true) WITH CHECK (true);

CREATE POLICY booking_groups_scope_policy
    ON public.booking_groups FOR ALL
    USING (user_id = auth.current_user_id())
    WITH CHECK (user_id = auth.current_user_id());

-- Location-scoped: anyone with a role at the location
-- A location's services and their config are public (the landing page shows
-- them before login), so queries filter by location themselves. The
-- services are created by the system only; admins change the config.
CREATE POLICY location_services_read_policy
    ON public.location_services FOR SELECT
    USING (true);

CREATE POLICY location_service_config_read_policy
    ON public.location_service_config FOR SELECT
    USING (true);

CREATE POLICY location_service_config_admin_update_policy
    ON public.location_service_config FOR UPDATE
    USING (auth.is_location_admin(location_id))
    WITH CHECK (auth.is_location_admin(location_id));

-- Staff see their location's kiosks; admins add and revoke them. The
-- tablets themselves never read this: they go through the kiosk_*
-- functions (schema/0004).
CREATE POLICY location_kiosk_devices_staff_read_policy
    ON public.location_kiosk_devices FOR SELECT
    USING (auth.is_location_staff(location_id));

CREATE POLICY location_kiosk_devices_admin_write_policy
    ON public.location_kiosk_devices FOR ALL
    USING (auth.is_location_admin(location_id))
    WITH CHECK (auth.is_location_admin(location_id));

CREATE POLICY location_service_days_scope_policy
    ON public.location_service_days FOR ALL
    USING (auth.has_location_role(location_id))
    WITH CHECK (auth.has_location_role(location_id));

-- User + location scoped
CREATE POLICY child_profile_scope_policy
    ON public.child_profile FOR ALL
    USING (auth.can_access_location_row(location_id, user_id))
    WITH CHECK (auth.can_access_location_row(location_id, user_id));

CREATE POLICY bookings_scope_policy
    ON public.bookings FOR ALL
    USING (auth.can_access_location_row(location_id, user_id))
    WITH CHECK (auth.can_access_location_row(location_id, user_id));

CREATE POLICY payment_attempts_scope_policy
    ON public.payment_attempts FOR ALL
    USING (auth.can_access_location_row(location_id, user_id))
    WITH CHECK (auth.can_access_location_row(location_id, user_id));

CREATE POLICY refunds_scope_policy
    ON public.refunds FOR ALL
    USING (auth.can_access_location_row(location_id, user_id))
    WITH CHECK (auth.can_access_location_row(location_id, user_id));

-- Inherited from users
CREATE POLICY customer_profile_scope_policy
    ON public.customer_profile FOR ALL
    USING (
        user_id = auth.current_user_id()
        OR auth.can_manage_user(user_id)
    )
    WITH CHECK (
        user_id = auth.current_user_id()
        OR auth.can_manage_user(user_id)
    );

-- Own actions at locations you belong to, plus actions of users you
-- outrank at the action's location.
CREATE POLICY actions_scope_policy
    ON public.actions FOR ALL
    USING (
        (
            user_id = auth.current_user_id()
            AND auth.has_location_role(location_id)
        )
        OR auth.can_manage_user(user_id, location_id)
    )
    WITH CHECK (
        (
            user_id = auth.current_user_id()
            AND auth.has_location_role(location_id)
        )
        OR auth.can_manage_user(user_id, location_id)
    );

-- Read access follows child_profile: the family sees their child's review
-- status. Only staff and above change it; the family's edits reach it
-- through trg_child_profile_medical_review (schema/0004), never directly.
CREATE POLICY child_medical_state_read_policy
    ON public.child_medical_state FOR SELECT
    USING (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_medical_state.child_id
              AND auth.can_access_location_row(cp.location_id, cp.user_id)
        )
    );

-- Medical approval is an admin responsibility (docs/portals.md).
CREATE POLICY child_medical_state_admin_write_policy
    ON public.child_medical_state FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_medical_state.child_id
              AND auth.is_location_admin(cp.location_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_medical_state.child_id
              AND auth.is_location_admin(cp.location_id)
        )
    );

-- Staff's internal notes: location staff and above only, never the
-- family (permissions decide who writes: admins, on the website).
CREATE POLICY child_notes_scope_policy
    ON public.child_notes FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_notes.child_id
              AND auth.is_location_staff(cp.location_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_notes.child_id
              AND auth.is_location_staff(cp.location_id)
        )
    );

CREATE POLICY child_documents_scope_policy
    ON public.child_documents FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_documents.child_id
              AND auth.can_access_location_row(cp.location_id, cp.user_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.child_profile cp
            WHERE cp.id = child_documents.child_id
              AND auth.can_access_location_row(cp.location_id, cp.user_id)
        )
    );

-- The family's own list (and every list at the location for staff). The
-- ID check and kiosk fields are further limited to staff by
-- trg_authorized_pickup_persons_rules (schema/0004).
CREATE POLICY authorized_pickup_persons_scope_policy
    ON public.authorized_pickup_persons FOR ALL
    USING (auth.can_access_location_row(location_id, user_id))
    WITH CHECK (auth.can_access_location_row(location_id, user_id));

-- Inherited from bookings
CREATE POLICY attendance_records_scope_policy
    ON public.attendance_records FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM public.bookings b
            WHERE b.id = attendance_records.booking_id
              AND auth.can_access_location_row(b.location_id, b.user_id)
        )
    )
    WITH CHECK (
        EXISTS (
            SELECT 1 FROM public.bookings b
            WHERE b.id = attendance_records.booking_id
              AND auth.can_access_location_row(b.location_id, b.user_id)
        )
    );


-- =====================================================
-- EMAIL
-- =====================================================

ALTER TABLE public.email_messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.email_messages FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy.email_template_overrides ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy.email_template_overrides FORCE ROW LEVEL SECURITY;

-- Only the email service writes the log, in its own transaction with
-- app.email_writer on (app/integrations/email). It's how the log is kept
-- apart from every request's own RLS session, including the webhooks that
-- have none.
CREATE POLICY email_messages_writer_policy
    ON public.email_messages FOR ALL
    USING (current_setting('app.email_writer', true) = 'on')
    WITH CHECK (current_setting('app.email_writer', true) = 'on');

-- Location admins see what was sent from their location.
CREATE POLICY email_messages_admin_read_policy
    ON public.email_messages FOR SELECT
    USING (auth.is_location_admin(location_id));

-- Read when rendering emails. Not personal information, and like the
-- rest of tenancy, readable; writes come with tenant configuration.
CREATE POLICY email_template_overrides_read_policy
    ON tenancy.email_template_overrides FOR SELECT
    USING (true);


-- =====================================================
-- STAFF KIOSK
-- =====================================================

ALTER TABLE auth.staff_pins ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth.staff_pins FORCE ROW LEVEL SECURITY;
ALTER TABLE public.staff_shifts ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.staff_shifts FORCE ROW LEVEL SECURITY;

-- A staff member sees whether they have a PIN (never anyone else's).
-- Written only by set_staff_pin and staff_kiosk_login (schema/0004).
CREATE POLICY staff_pins_own_read_policy
    ON auth.staff_pins FOR SELECT
    USING (user_id = auth.current_user_id());

-- Staff see their own shifts at the session's location; admins see the
-- location's.
CREATE POLICY staff_shifts_read_policy
    ON public.staff_shifts FOR SELECT
    USING (
        (user_id = auth.current_user_id() AND auth.has_location_role(location_id))
        OR auth.is_location_admin(location_id)
    );


-- Enquiries (docs/enquiries.md): the centre's admins and superadmins read
-- them, close and reopen them, and reply. They arrive only through
-- public.submit_enquiry (no insert policy); nothing is deleted.
ALTER TABLE public.enquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.enquiries FORCE ROW LEVEL SECURITY;

CREATE POLICY enquiries_admin_read_policy
    ON public.enquiries FOR SELECT
    USING (auth.is_location_admin(location_id));

CREATE POLICY enquiries_admin_update_policy
    ON public.enquiries FOR UPDATE
    USING (auth.is_location_admin(location_id))
    WITH CHECK (auth.is_location_admin(location_id));

ALTER TABLE public.enquiry_replies ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.enquiry_replies FORCE ROW LEVEL SECURITY;

CREATE POLICY enquiry_replies_admin_read_policy
    ON public.enquiry_replies FOR SELECT
    USING (auth.is_location_admin(location_id));

CREATE POLICY enquiry_replies_admin_write_policy
    ON public.enquiry_replies FOR INSERT
    WITH CHECK (auth.is_location_admin(location_id));


-- Enquiries to the platform itself (docs/platform-site.md): only the
-- platform's admins read them and mark them dealt with. They arrive only
-- through public.submit_platform_enquiry (no insert policy).
ALTER TABLE public.platform_enquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_enquiries FORCE ROW LEVEL SECURITY;

CREATE POLICY platform_enquiries_read_policy
    ON public.platform_enquiries FOR SELECT
    USING (auth.is_platform_admin());

CREATE POLICY platform_enquiries_close_policy
    ON public.platform_enquiries FOR UPDATE
    USING (auth.is_platform_admin())
    WITH CHECK (auth.is_platform_admin());


-- The platform's landing page (docs/platform-site.md): anyone reads it;
-- only the platform's admins change it. Its one row is made by the seeds,
-- and features are saved as a whole list (delete, then insert).
ALTER TABLE public.platform_site ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_site FORCE ROW LEVEL SECURITY;

CREATE POLICY platform_site_read_policy
    ON public.platform_site FOR SELECT
    USING (true);

CREATE POLICY platform_site_update_policy
    ON public.platform_site FOR UPDATE
    USING (auth.is_platform_admin())
    WITH CHECK (auth.is_platform_admin());

ALTER TABLE public.platform_features ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.platform_features FORCE ROW LEVEL SECURITY;

CREATE POLICY platform_features_read_policy
    ON public.platform_features FOR SELECT
    USING (true);

CREATE POLICY platform_features_write_policy
    ON public.platform_features FOR ALL
    USING (auth.is_platform_admin())
    WITH CHECK (auth.is_platform_admin());
