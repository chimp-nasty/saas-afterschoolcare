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
    address TEXT,
    phone VARCHAR(50),
    email VARCHAR(255),

    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT fk_locations_tenant
        FOREIGN KEY (tenant_id)
        REFERENCES tenancy.tenants (id)
        ON DELETE CASCADE,

    CONSTRAINT uq_locations_tenant_code
        UNIQUE (tenant_id, code),

    CONSTRAINT ck_locations_code_format
        CHECK (code ~ '^[a-z][a-z0-9-]*$')
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
