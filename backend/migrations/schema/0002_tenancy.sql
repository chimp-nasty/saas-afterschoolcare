-- =====================================================
-- TENANTS
-- =====================================================

-- An Australian Business Number: 11 digits passing the ABR's check
-- (subtract 1 from the first digit, weight the digits 10, 1, 3, 5, ... 19,
-- and the sum divides by 89).
CREATE FUNCTION tenancy.is_valid_abn(p_abn text)
RETURNS boolean
LANGUAGE sql
IMMUTABLE
AS $$
    SELECT p_abn ~ '^[0-9]{11}$'
       AND (
           SELECT sum(
               (substr(p_abn, i, 1)::int - CASE WHEN i = 1 THEN 1 ELSE 0 END)
               * (ARRAY[10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19])[i]
           )
           FROM generate_series(1, 11) AS i
       ) % 89 = 0;
$$;

CREATE TABLE tenancy.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL,
    custom_domain VARCHAR(255),
    email VARCHAR(255),

    -- The business's details (Business settings, its owner): shown to
    -- families and on its landing page. Unset until the owner fills them in.
    legal_name VARCHAR(200),
    abn CHAR(11),
    phone VARCHAR(50),
    about VARCHAR(1000),
    -- The landing page's headline ("After school care, made easy").
    tagline VARCHAR(120),

    terms_accepted_at TIMESTAMPTZ NOT NULL,
    terms_version VARCHAR(50) NOT NULL DEFAULT 'v1',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_tenants_code
        UNIQUE (code),

    CONSTRAINT uq_tenants_custom_domain
        UNIQUE (custom_domain),

    CONSTRAINT ck_tenants_code_format
        CHECK (code ~ '^[a-z][a-z0-9-]*$'),

    -- The code is the tenant's subdomain (after3.<platform domain>); these
    -- belong to the platform.
    CONSTRAINT ck_tenants_code_reserved
        CHECK (code NOT IN ('www', 'api', 'platform', 'admin', 'mail', 'app')),

    CONSTRAINT ck_tenants_name_not_blank
        CHECK (btrim(name) <> ''),

    CONSTRAINT ck_tenants_abn
        CHECK (abn IS NULL OR tenancy.is_valid_abn(abn))
);


-- =====================================================
-- LOCATIONS
-- =====================================================

CREATE TABLE tenancy.locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id UUID NOT NULL,

    name VARCHAR(200) NOT NULL,
    -- The first part of its address (/varsity). The owner may change it;
    -- old links then lead to the tenant's landing page.
    code VARCHAR(50) NOT NULL,
    -- Where the location's services run, shown to families (a service may
    -- get its own venue later). Australian addresses only.
    address_line_1 VARCHAR(255) NOT NULL,
    address_line_2 VARCHAR(255),
    suburb VARCHAR(100) NOT NULL,
    state VARCHAR(3) NOT NULL,
    postcode CHAR(4) NOT NULL,

    -- For maps, not integrated yet: set once the address is geocoded.
    latitude NUMERIC(9, 6),
    longitude NUMERIC(9, 6),
    google_place_id TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),

    -- "Today" depends on where the location is: session times, booking
    -- and refund cut-offs and attendance all use it.
    timezone TEXT NOT NULL DEFAULT 'Australia/Brisbane',

    -- Children can be signed in and out (at either kiosk) only from 2 hours
    -- before a session to 2 hours after it
    -- (public.service_day_signing_window); anything outside that is dealt
    -- with in person. Admins switch it off and on (/admin/kiosks).
    kiosk_enforce_service_times BOOLEAN NOT NULL DEFAULT TRUE,

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_locations_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_locations_tenant_code
        UNIQUE (tenant_id, code),

    -- Target for authorized_pickup_persons' composite foreign key.
    CONSTRAINT uq_locations_id_tenant
        UNIQUE (id, tenant_id),

    CONSTRAINT ck_locations_code_format
        CHECK (code ~ '^[a-z][a-z0-9-]*$'),

    -- The code is the first part of the location's address (/varsity),
    -- where the site's own pages also live (/business, /api).
    CONSTRAINT ck_locations_code_reserved
        CHECK (code NOT IN (
            'business', 'api', 'platform', 'register',
            'kiosk', 'staff', 'login', 'demo'
        )),

    CONSTRAINT ck_locations_name_not_blank
        CHECK (btrim(name) <> ''),

    CONSTRAINT ck_locations_timezone
        CHECK (timezone IN (
            'Australia/Brisbane', 'Australia/Sydney', 'Australia/Melbourne',
            'Australia/Hobart', 'Australia/Adelaide', 'Australia/Darwin',
            'Australia/Perth', 'Australia/Broken_Hill', 'Australia/Lord_Howe',
            'Australia/Eucla'
        )),

    CONSTRAINT ck_locations_address_not_blank
        CHECK (btrim(address_line_1) <> '' AND btrim(suburb) <> ''),

    CONSTRAINT ck_locations_state
        CHECK (state IN ('NSW', 'VIC', 'QLD', 'WA', 'SA', 'TAS', 'ACT', 'NT')),

    CONSTRAINT ck_locations_postcode
        CHECK (postcode ~ '^[0-9]{4}$'),

    CONSTRAINT ck_locations_coordinates
        CHECK ((latitude IS NULL) = (longitude IS NULL))
);


-- =====================================================
-- TENANT BRANDING
-- =====================================================

-- How the business looks, on its landing page and every centre's pages
-- (one brand per business; docs/tenant-administration.md, stage 5). Set by
-- its owner in Business settings › Your site. Files live in the document
-- bucket under branding/tenants/{tenant}/ (keys hold only IDs). No row, or
-- an empty field, means the app's defaults.
CREATE TABLE tenancy.tenant_branding (
    tenant_id UUID PRIMARY KEY,

    -- Any shape: the page header and landing page.
    logo_key TEXT,
    -- Square: the browser tab, bookmarks and home screens. Without one the
    -- logo is used, then the platform's icon.
    icon_key TEXT,

    primary_color VARCHAR(7),
    secondary_color VARCHAR(7),

    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_tenant_branding_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT ck_tenant_branding_colors
        CHECK (
            (primary_color IS NULL OR primary_color ~ '^#[0-9A-Fa-f]{6}$')
            AND (secondary_color IS NULL OR secondary_color ~ '^#[0-9A-Fa-f]{6}$')
        )
);

CREATE TRIGGER trg_tenant_branding_updated_at
    BEFORE UPDATE ON tenancy.tenant_branding
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();


-- =====================================================
-- TENANT FAQS
-- =====================================================

-- Questions and answers on the landing page, in the owner's order. Saved
-- as a whole list (Business settings › Your site); at most 20.
CREATE TABLE tenancy.tenant_faqs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id UUID NOT NULL,

    position INTEGER NOT NULL,
    question VARCHAR(200) NOT NULL,
    answer VARCHAR(2000) NOT NULL,

    CONSTRAINT fk_tenant_faqs_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_tenant_faqs_position
        UNIQUE (tenant_id, position),

    CONSTRAINT ck_tenant_faqs_text
        CHECK (btrim(question) <> '' AND btrim(answer) <> '')
);

CREATE FUNCTION tenancy.enforce_tenant_faq_limit()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF (SELECT count(*) FROM tenancy.tenant_faqs WHERE tenant_id = NEW.tenant_id) > 20 THEN
        RAISE EXCEPTION 'A business has at most 20 questions'
            USING ERRCODE = 'check_violation',
                  CONSTRAINT = 'ck_tenant_faqs_limit',
                  TABLE = 'tenant_faqs',
                  SCHEMA = 'tenancy';
    END IF;

    RETURN NEW;
END;
$$;

CREATE TRIGGER trg_tenant_faqs_limit
    AFTER INSERT ON tenancy.tenant_faqs
    FOR EACH ROW EXECUTE FUNCTION tenancy.enforce_tenant_faq_limit();

-- =====================================================
-- TENANT STRIPE ACCOUNTS (Stripe Connect)
-- =====================================================

-- Each tenant is paid into its own Stripe account (a Standard connected
-- account, direct charges: the centre is the seller, owns payouts and
-- disputes). We store only its id and what Stripe last told us about it,
-- never a secret key. One per tenant; every centre of the tenant uses it.
--
--   * connected by a superadmin (Admin › Payments) through Stripe's hosted
--     onboarding; Stripe's account.updated webhook keeps the flags current
--     (sync_stripe_account, server code only)
--   * disconnected_at: the tenant turned payments off in our app. New
--     payments stop; refunds of past payments still go through the account
--     (each payment keeps the account it used, payment_attempts)
--   * revoked_at: the tenant removed our access in their Stripe dashboard.
--     We can no longer act on the account; refunds are made there
CREATE TABLE tenancy.tenant_stripe_accounts (
    tenant_id UUID PRIMARY KEY,

    stripe_account_id VARCHAR(255) NOT NULL,
    -- The business linked an account it already had ("Connect with
    -- Stripe", OAuth) rather than us creating one. A linked account
    -- finishes any setup in its own Stripe dashboard; only accounts we
    -- created use our onboarding link.
    is_linked BOOLEAN NOT NULL DEFAULT FALSE,

    charges_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    payouts_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    details_submitted BOOLEAN NOT NULL DEFAULT FALSE,

    connected_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    disconnected_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_tenant_stripe_accounts_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_tenant_stripe_accounts_account
        UNIQUE (stripe_account_id)
);

CREATE TRIGGER trg_tenant_stripe_accounts_updated_at
    BEFORE UPDATE ON tenancy.tenant_stripe_accounts
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

-- The Stripe account a tenant's payments go to, or NULL while it can't
-- take payments (not connected, onboarding unfinished, disconnected in our
-- app, or access revoked). New bookings and checkouts need one (the
-- booking rules, trg_payment_attempts_account). SECURITY DEFINER: anyone
-- may ask whether a centre takes bookings (the public site shows it).
CREATE FUNCTION tenancy.tenant_payments_account(p_tenant_id UUID)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, tenancy
AS $$
    SELECT a.stripe_account_id::text
    FROM tenancy.tenant_stripe_accounts a
    WHERE a.tenant_id = p_tenant_id
      AND a.charges_enabled
      AND a.details_submitted
      AND a.disconnected_at IS NULL
      AND a.revoked_at IS NULL;
$$;

-- The same for a location: its tenant's account.
CREATE FUNCTION tenancy.payments_account(p_location_id UUID)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, tenancy
AS $$
    SELECT tenancy.tenant_payments_account(l.tenant_id)
    FROM tenancy.locations l
    WHERE l.id = p_location_id;
$$;

-- What Stripe says about a connected account (its account.updated and
-- account.application.deauthorized webhooks). Server code only: refused
-- inside a user's session (auth.current_user_id, schema/0005, read at run
-- time). Returns whether the account is ours.
CREATE FUNCTION tenancy.sync_stripe_account(
    p_stripe_account_id TEXT,
    p_charges_enabled BOOLEAN,
    p_payouts_enabled BOOLEAN,
    p_details_submitted BOOLEAN,
    p_revoked BOOLEAN
)
RETURNS boolean
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = pg_catalog, tenancy, public
AS $$
BEGIN
    IF auth.current_user_id() IS NOT NULL THEN
        RAISE EXCEPTION 'Only Stripe''s webhooks update connected accounts'
            USING ERRCODE = 'insufficient_privilege';
    END IF;

    UPDATE tenancy.tenant_stripe_accounts
    SET charges_enabled = CASE WHEN p_revoked THEN charges_enabled ELSE p_charges_enabled END,
        payouts_enabled = CASE WHEN p_revoked THEN payouts_enabled ELSE p_payouts_enabled END,
        details_submitted = CASE WHEN p_revoked THEN details_submitted ELSE p_details_submitted END,
        revoked_at = CASE WHEN p_revoked THEN COALESCE(revoked_at, now()) ELSE revoked_at END
    WHERE stripe_account_id = p_stripe_account_id;

    RETURN FOUND;
END;
$$;
