-- The role the app connects as (DATABASE_URL). It has no BYPASSRLS, so
-- every query goes through the policies in 0005_rls.sql.
--
-- The password comes from APP_DB_PASSWORD, which the migrator passes in
-- as the app.runtime_password setting, so it never lives in the repo.
-- Re-running sets the password again, keeping it in sync with the env.

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_roles WHERE rolname = 'app_user'
    ) THEN
        EXECUTE format(
            'CREATE ROLE app_user LOGIN PASSWORD %L '
            'NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT '
            'NOREPLICATION NOBYPASSRLS',
            current_setting('app.runtime_password')
        );
    ELSE
        EXECUTE format(
            'ALTER ROLE app_user WITH LOGIN PASSWORD %L',
            current_setting('app.runtime_password')
        );
    END IF;
END
$$;


-- =====================================================
-- SCHEMA ACCESS
-- =====================================================

GRANT USAGE ON SCHEMA public, auth, tenancy TO app_user;


-- =====================================================
-- PUBLIC
-- =====================================================

GRANT SELECT, INSERT, UPDATE, DELETE
    ON ALL TABLES IN SCHEMA public
    TO app_user;


-- =====================================================
-- AUTH
-- =====================================================

-- Read auth configuration / identity data.
GRANT SELECT ON ALL TABLES IN SCHEMA auth TO app_user;

-- Registration and account updates.
GRANT INSERT, UPDATE ON auth.users TO app_user;

-- Membership creation / management.
GRANT INSERT, UPDATE, DELETE ON auth.location_user_roles TO app_user;

-- Forgot / reset password.
GRANT INSERT, UPDATE ON auth.password_reset_tokens TO app_user;

-- The platform's site: a platform admin's last login, and invites (RLS:
-- platform admins only).
GRANT UPDATE ON auth.platform_admins TO app_user;
GRANT INSERT, UPDATE ON auth.tenant_invites TO app_user;


-- =====================================================
-- TENANCY
-- =====================================================

GRANT SELECT ON ALL TABLES IN SCHEMA tenancy TO app_user;

-- The tenant's owner connects and disconnects its Stripe account, changes
-- the business's details and adds and edits its locations (RLS limits each
-- to their own tenant and their tenant permissions).
GRANT INSERT, UPDATE ON tenancy.tenant_stripe_accounts TO app_user;
GRANT UPDATE ON tenancy.tenants TO app_user;
GRANT INSERT, UPDATE ON tenancy.locations TO app_user;

-- Its site (stage 5): branding, FAQs (saved as a whole list) and policy
-- documents (added, never changed).
GRANT INSERT, UPDATE ON tenancy.tenant_branding TO app_user;
GRANT INSERT, UPDATE, DELETE ON tenancy.tenant_faqs TO app_user;
GRANT INSERT ON tenancy.tenant_documents TO app_user;


-- =====================================================
-- SEQUENCES
-- =====================================================

GRANT USAGE, SELECT
    ON ALL SEQUENCES IN SCHEMA public, auth
    TO app_user;


-- =====================================================
-- FUTURE OBJECTS
-- =====================================================
-- Tables and sequences created by later migrations get the same baseline
-- access automatically. Anything beyond the baseline (like the auth
-- write grants above) still needs an explicit GRANT in that migration.

ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA auth
    GRANT SELECT ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA tenancy
    GRANT SELECT ON TABLES TO app_user;

ALTER DEFAULT PRIVILEGES IN SCHEMA public, auth
    GRANT USAGE, SELECT ON SEQUENCES TO app_user;
