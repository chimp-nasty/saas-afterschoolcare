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
