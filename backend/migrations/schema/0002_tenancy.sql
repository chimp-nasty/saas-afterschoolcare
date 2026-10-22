-- =====================================================
-- TENANTS
-- =====================================================

CREATE TABLE tenancy.tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    name VARCHAR(200) NOT NULL,
    code VARCHAR(50) NOT NULL,
    custom_domain VARCHAR(255),
    email VARCHAR(255),

    terms_accepted_at TIMESTAMPTZ NOT NULL,
    terms_version VARCHAR(50) NOT NULL DEFAULT 'v1',

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT uq_tenants_code
        UNIQUE (code),

    CONSTRAINT uq_tenants_custom_domain
        UNIQUE (custom_domain),

    CONSTRAINT ck_tenants_code_format
        CHECK (code ~ '^[a-z][a-z0-9-]*$')
);


-- =====================================================
-- LOCATIONS
-- =====================================================

CREATE TABLE tenancy.locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    tenant_id UUID NOT NULL,

    name VARCHAR(200),
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
-- LOCATION BRANDING
-- =====================================================

CREATE TABLE tenancy.location_branding (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    location_id UUID NOT NULL,

    display_name VARCHAR(200),
    logo_key TEXT,
    primary_color VARCHAR(50),
    secondary_color VARCHAR(50),
    font_family VARCHAR(100),

    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_location_branding_location
        FOREIGN KEY (location_id)
        REFERENCES tenancy.locations (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_location_branding_location
        UNIQUE (location_id)
);

CREATE TRIGGER trg_location_branding_updated_at
    BEFORE UPDATE ON tenancy.location_branding
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

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

-- The Stripe account a location's payments go to, or NULL while it can't
-- take payments (not connected, onboarding unfinished, disconnected in our
-- app, or access revoked). New bookings and checkouts need one (the
-- booking rules, trg_payment_attempts_account). SECURITY DEFINER: anyone
-- may ask whether a centre takes bookings (the public site shows it).
CREATE FUNCTION tenancy.payments_account(p_location_id UUID)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = pg_catalog, tenancy
AS $$
    SELECT a.stripe_account_id::text
    FROM tenancy.locations l
    JOIN tenancy.tenant_stripe_accounts a
        ON a.tenant_id = l.tenant_id
    WHERE l.id = p_location_id
      AND a.charges_enabled
      AND a.details_submitted
      AND a.disconnected_at IS NULL
      AND a.revoked_at IS NULL;
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
