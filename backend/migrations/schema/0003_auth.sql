-- =====================================================
-- USERS
-- =====================================================

CREATE TABLE auth.users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,

    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    terms_accepted_at TIMESTAMPTZ NOT NULL,
    terms_version VARCHAR(50) NOT NULL DEFAULT 'v1',

    is_active BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login TIMESTAMPTZ,

    CONSTRAINT uq_users_email
        UNIQUE (email)
);


-- =====================================================
-- STAFF PINS
-- =====================================================

-- A staff member's 4-digit PIN for the staff kiosk, where it records who
-- did what. One per person, used at every location they work at. Set or
-- changed only on the website, after re-entering their password
-- (public.set_staff_pin); only its hash is kept. Five wrong PINs at the
-- kiosk lock it until they set a new one.
CREATE TABLE auth.staff_pins (
    user_id UUID PRIMARY KEY,

    pin_hash TEXT NOT NULL,
    failed_pin_attempts SMALLINT NOT NULL DEFAULT 0,
    pin_locked_at TIMESTAMPTZ,
    set_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_staff_pins_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT ck_staff_pins_failed_pin_attempts
        CHECK (failed_pin_attempts >= 0)
);


-- =====================================================
-- PASSWORD RESET TOKENS
-- =====================================================

-- A reset is requested at one location (the user must have a role there):
-- its emails go out as that centre, linking back to its site.
CREATE TABLE auth.password_reset_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,

    token_hash TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_password_reset_tokens_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_password_reset_tokens_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_password_reset_tokens_token_hash
        UNIQUE (token_hash)
);


-- =====================================================
-- ROLES
-- =====================================================

CREATE TABLE auth.roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    code VARCHAR(100) NOT NULL,
    name VARCHAR(200) NOT NULL,
    description TEXT,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_roles_code
        UNIQUE (code),

    CONSTRAINT ck_roles_code_format
        CHECK (code ~ '^[a-z][a-z0-9_]*$')
);


-- =====================================================
-- PERMISSIONS
-- =====================================================

CREATE TABLE auth.permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    resource VARCHAR(100) NOT NULL,
    action VARCHAR(1) NOT NULL,
    scope auth.permission_scope_enum NOT NULL DEFAULT 'location',
    description TEXT,

    CONSTRAINT uq_permissions_resource_action
        UNIQUE (resource, action),

    -- Target for the scoped foreign keys below: roles only hold location
    -- permissions, owners only tenant ones.
    CONSTRAINT uq_permissions_id_scope
        UNIQUE (id, scope),

    CONSTRAINT ck_permissions_action
        CHECK (action IN ('c', 'r', 'u', 'd')),

    CONSTRAINT ck_permissions_resource_format
        CHECK (resource ~ '^[a-z][a-z0-9_]*$')
);


-- =====================================================
-- ROLE PERMISSIONS
-- =====================================================

-- A role's permission on one channel (docs/portals.md, section 2): the
-- same role can do different things on the website and at the staff kiosk.
-- Roles are held at a location, so they only take location permissions.
CREATE TABLE auth.role_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    role_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    channel auth.permission_channel_enum NOT NULL,
    scope auth.permission_scope_enum NOT NULL DEFAULT 'location',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_role_permissions_role
        FOREIGN KEY (role_id)
        REFERENCES auth.roles (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_role_permissions_permission
        FOREIGN KEY (permission_id, scope)
        REFERENCES auth.permissions (id, scope)
        ON DELETE CASCADE,

    CONSTRAINT ck_role_permissions_scope
        CHECK (scope = 'location'),

    CONSTRAINT uq_role_permissions_role_permission_channel
        UNIQUE (role_id, permission_id, channel)
);


-- =====================================================
-- LOCATION USER ROLES
-- =====================================================

CREATE TABLE auth.location_user_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    location_id UUID NOT NULL,
    role_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_location_user_roles_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_location_user_roles_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_location_user_roles_role
        FOREIGN KEY (role_id)
        REFERENCES auth.roles (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_location_user_roles_user_location_role
        UNIQUE (user_id, location_id, role_id)
);


-- =====================================================
-- TENANT OWNERS
-- =====================================================

-- The one person who runs a tenant (docs/tenant-administration.md):
-- created at registration, superadmin at every one of its locations (the
-- triggers below) and the only holder of tenant permissions. One tenant
-- per owner. Kept here rather than on tenancy.tenants, which is created
-- before auth.users.
CREATE TABLE auth.tenant_owners (
    tenant_id UUID PRIMARY KEY,

    user_id UUID NOT NULL,

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_tenant_owners_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_tenant_owners_user
        FOREIGN KEY (user_id)
        REFERENCES auth.users (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_tenant_owners_user
        UNIQUE (user_id),

    -- Target for user_tenant_permissions' composite foreign key.
    CONSTRAINT uq_tenant_owners_tenant_user
        UNIQUE (tenant_id, user_id)
);


-- =====================================================
-- USER TENANT PERMISSIONS
-- =====================================================

-- What a user may do across the whole tenant (its settings, locations,
-- Stripe, domains), granted to the user directly rather than through a
-- role. Only the tenant's owner holds them (the foreign key to
-- tenant_owners). Read at login into the token's tenant_permissions, and
-- live by RLS (auth.has_tenant_permission).
CREATE TABLE auth.user_tenant_permissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    user_id UUID NOT NULL,
    tenant_id UUID NOT NULL,
    permission_id UUID NOT NULL,
    scope auth.permission_scope_enum NOT NULL DEFAULT 'tenant',

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_user_tenant_permissions_owner
        FOREIGN KEY (tenant_id, user_id)
        REFERENCES auth.tenant_owners (tenant_id, user_id)
        ON DELETE CASCADE,

    CONSTRAINT fk_user_tenant_permissions_permission
        FOREIGN KEY (permission_id, scope)
        REFERENCES auth.permissions (id, scope)
        ON DELETE CASCADE,

    CONSTRAINT ck_user_tenant_permissions_scope
        CHECK (scope = 'tenant'),

    CONSTRAINT uq_user_tenant_permissions_user_tenant_permission
        UNIQUE (user_id, tenant_id, permission_id)
);


-- =====================================================
-- OWNER IS SUPERADMIN EVERYWHERE
-- =====================================================

-- The tenant's owner is superadmin at every location of the tenant: at
-- the existing ones when they become owner, and at each new one as it's
-- added. plpgsql because the roles are seeded after the schema.
-- auth.enforce_staff_role_rules (schema/0004) lets these through.
CREATE FUNCTION auth.grant_owner_superadmin(
    p_tenant_id uuid,
    p_location_id uuid DEFAULT NULL
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    INSERT INTO auth.location_user_roles (user_id, location_id, role_id)
    SELECT o.user_id, l.id, r.id
    FROM auth.tenant_owners o
    JOIN tenancy.locations l
        ON l.tenant_id = o.tenant_id
    JOIN auth.roles r
        ON r.code = 'superadmin'
    WHERE o.tenant_id = p_tenant_id
      AND (p_location_id IS NULL OR l.id = p_location_id)
    ON CONFLICT (user_id, location_id, role_id) DO NOTHING;
END;
$$;

CREATE FUNCTION auth.grant_owner_superadmin_on_owner()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    PERFORM auth.grant_owner_superadmin(NEW.tenant_id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tenant_owners_grant_superadmin
    AFTER INSERT ON auth.tenant_owners
    FOR EACH ROW EXECUTE FUNCTION auth.grant_owner_superadmin_on_owner();

CREATE FUNCTION auth.grant_owner_superadmin_on_location()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    PERFORM auth.grant_owner_superadmin(NEW.tenant_id, NEW.id);
    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_locations_grant_owner_superadmin
    AFTER INSERT ON tenancy.locations
    FOR EACH ROW EXECUTE FUNCTION auth.grant_owner_superadmin_on_location();


-- =====================================================
-- PLATFORM ADMINS
-- =====================================================

-- The platform's own people (docs/tenant-administration.md): they invite
-- businesses and switch tenants off and on, on the platform's site, and
-- never see a tenant's data. Not in auth.users, so a platform login can't
-- sign in to a tenant, nor the other way round. Created by the dev seed,
-- or by hand in production (no screen).
CREATE TABLE auth.platform_admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email VARCHAR(255) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login TIMESTAMPTZ,

    CONSTRAINT uq_platform_admins_email
        UNIQUE (email)
);


-- =====================================================
-- TENANT INVITES
-- =====================================================

-- Registration is by invite only: a platform admin makes a one-time link
-- for an email (the link carries the token; we keep only its hash) and
-- sends it themselves. Registering with it (auth.register_tenant) creates
-- the tenant and its owner, and uses the invite up. A week to use it.
CREATE TABLE auth.tenant_invites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    email VARCHAR(255) NOT NULL,
    token_hash VARCHAR(255) NOT NULL,

    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at TIMESTAMPTZ NOT NULL DEFAULT now() + interval '7 days',

    revoked_at TIMESTAMPTZ,

    -- Set together when the invite is used.
    used_at TIMESTAMPTZ,
    tenant_id UUID,

    CONSTRAINT fk_tenant_invites_created_by
        FOREIGN KEY (created_by)
        REFERENCES auth.platform_admins (id),

    CONSTRAINT fk_tenant_invites_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE SET NULL,

    CONSTRAINT uq_tenant_invites_token_hash
        UNIQUE (token_hash),

    -- Only a used invite names its tenant (cleared if the tenant goes).
    CONSTRAINT ck_tenant_invites_used
        CHECK (tenant_id IS NULL OR used_at IS NOT NULL)
);


-- =====================================================
-- REGISTRATION
-- =====================================================

-- The email an invite is for, while it can still be used (the registration
-- page shows it before anyone has a session), or NULL.
CREATE FUNCTION auth.usable_invite_email(p_token_hash text)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
    SELECT i.email::text
    FROM auth.tenant_invites i
    WHERE i.token_hash = p_token_hash
      AND i.used_at IS NULL
      AND i.revoked_at IS NULL
      AND i.expires_at > now();
$$;

-- A business registering with its invite: the tenant, its owner (with every
-- tenant permission; the tenant_owners trigger makes them superadmin at its
-- locations as they're added), and the invite used up, all at once. The
-- owner's email is the invite's. SECURITY DEFINER: registration has no
-- session, and nothing else may create tenants. plpgsql: it reads the
-- seeded permissions at run time.
CREATE FUNCTION auth.register_tenant(
    p_token_hash text,
    p_tenant_name text,
    p_tenant_code text,
    p_first_name text,
    p_last_name text,
    p_password_hash text
)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
DECLARE
    v_invite auth.tenant_invites;
    v_tenant_id uuid;
    v_user_id uuid;
BEGIN
    SELECT * INTO v_invite
    FROM auth.tenant_invites
    WHERE token_hash = p_token_hash
    FOR UPDATE;

    IF NOT FOUND
       OR v_invite.used_at IS NOT NULL
       OR v_invite.revoked_at IS NOT NULL
       OR v_invite.expires_at <= now() THEN
        RAISE EXCEPTION 'This invite can''t be used'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_tenant_invites_usable',
                  TABLE = 'tenant_invites',
                  SCHEMA = 'auth';
    END IF;

    INSERT INTO tenancy.tenants (name, code, email, terms_accepted_at)
    VALUES (p_tenant_name, p_tenant_code, v_invite.email, now())
    RETURNING id INTO v_tenant_id;

    INSERT INTO auth.users (
        email, password_hash, first_name, last_name,
        terms_accepted_at, is_active
    )
    VALUES (v_invite.email, p_password_hash, p_first_name, p_last_name, now(), TRUE)
    RETURNING id INTO v_user_id;

    INSERT INTO auth.tenant_owners (tenant_id, user_id)
    VALUES (v_tenant_id, v_user_id);

    INSERT INTO auth.user_tenant_permissions (user_id, tenant_id, permission_id)
    SELECT v_user_id, v_tenant_id, p.id
    FROM auth.permissions p
    WHERE p.scope = 'tenant';

    UPDATE auth.tenant_invites
    SET used_at = now(),
        tenant_id = v_tenant_id
    WHERE id = v_invite.id;

    RETURN v_tenant_id;
END;
$$;

-- A platform admin switches a tenant off (its site and logins answer as if
-- it didn't exist; Stripe's webhooks still settle what's under way) or back
-- on. Only that column, and only for a platform admin (auth.is_platform_admin,
-- schema/0005).
CREATE FUNCTION auth.set_tenant_active(
    p_tenant_id uuid,
    p_active boolean
)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, public
AS $$
BEGIN
    IF NOT auth.is_platform_admin() THEN
        RAISE EXCEPTION 'Only the platform can switch a tenant off or on'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_tenants_active_platform_only',
                  TABLE = 'tenants',
                  SCHEMA = 'tenancy';
    END IF;

    UPDATE tenancy.tenants
    SET is_active = p_active
    WHERE id = p_tenant_id;
END;
$$;


-- =====================================================
-- TENANT DOCUMENTS
-- =====================================================

-- The business's policies as PDFs (Business settings › Your site): its
-- privacy policy and its terms, linked from its landing page; families
-- accept the current terms when they sign up (customer_profile.
-- terms_document_id). Never changed or removed: each upload is a new
-- version, the latest is current, so what a family accepted stays on
-- record. Here rather than in 0002 because uploaded_by is an auth.users row.
CREATE TABLE tenancy.tenant_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id UUID NOT NULL,
    kind VARCHAR(20) NOT NULL,

    storage_key TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,

    uploaded_by UUID NOT NULL,
    uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_tenant_documents_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT fk_tenant_documents_uploaded_by
        FOREIGN KEY (uploaded_by)
        REFERENCES auth.users (id),

    CONSTRAINT ck_tenant_documents_kind
        CHECK (kind IN ('privacy', 'terms')),

    -- 5 MB, as the upload allows.
    CONSTRAINT ck_tenant_documents_size
        CHECK (size_bytes BETWEEN 1 AND 5242880)
);

CREATE INDEX ix_tenant_documents_current
    ON tenancy.tenant_documents (tenant_id, kind, uploaded_at DESC);
