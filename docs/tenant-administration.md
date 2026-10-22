# Tenant administration, onboarding and the platform owner

**Status:** Agreed in discussion 23 October 2026; not built. MVP step 5 (tenant configuration), following Stripe Connect.

**Principle:** extend the location-scoped login rather than replace it. One login system, one cookie per tenant site, an optional location. Tenant-wide settings live at `/business`, outside any location. The platform owner is a separate identity that never sees tenant data.

**Terms:** in code and in this doc it's a *location*; families and staff see *centre*.

---

## 1. Decisions

| Topic | Decision |
|---|---|
| Who runs a tenant | One owner per tenant, created at registration. They are the tenant's only superadmin and hold every tenant permission. No screen for granting tenant permissions to others. |
| Owner at new locations | Adding a location gives the owner the superadmin role there (a database trigger, not the endpoint). |
| Tenant permissions | Same `(resource, action)` catalogue as now, with a `scope` (`location` or `tenant`). Location permissions are granted to roles, tenant permissions directly to users; the schema refuses mixing them. |
| Token | The existing JWT plus `tenant_id` and `tenant_permissions`; `location_id` becomes optional. A token without a location gets 403 from every location endpoint. |
| Tenant binding | Every authenticated request checks the token's tenant against the site's tenant (from the host). |
| API location | Same origin on every tenant host: `https://<tenant host>/api/...`, through a reverse proxy. Cookies become first-party and per tenant site; custom domains work; `SameSite` moves from `None` to `Lax`. |
| Tenant pages | `/business` (shown as "Business settings"). `/{location}/admin` stays the location's admin portal. |
| Switching location | An authenticated endpoint reissues the cookie for another location where the user has a role. Used from "Manage centre" on `/business`. The "signed in at another centre" screen stays as is. |
| Registration | Invite-only. The platform owner sends a one-time link; the business registers and lands in `/business`. |
| Platform owner | Separate login and token audience. Invites businesses, lists tenants, deactivates them. No access to tenant data. |
| Known gaps, accepted | Permission changes take up to the 90-minute token lifetime to reach the token (the database checks tenant permissions live). Ownership transfer is out of the MVP. A family using two providers on the platform needs two emails (emails are unique platform-wide). |

## 2. Data

Schema changes edit the original files (root `CLAUDE.md`).

**`0002_tenancy.sql`**
- `tenancy.locations`: a location's code is the first part of its URL (`/varsity`), and the same place now holds fixed pages (`/business`, `/api`). A location coded `business` would make `/business` ambiguous, so `ck_locations_code_reserved` refuses `business`, `api`, `platform`, `register`, `kiosk`, `staff`, `login`, `demo`.
- `tenancy.tenants`: business details for settings and the landing page (legal name, ABN, contact email and phone, short introduction). `custom_domain` stays; domain status columns are added with stage 6.
- `tenancy.tenant_invites`: `token_hash`, `email`, `expires_at`, `used_at`, `tenant_id` (set on use), `created_at`. Written only by platform and registration code.

**`0003_auth.sql`**
- `auth.permissions.scope` (`location` | `tenant`), unique on `(id, scope)`.
- `auth.role_permissions` carries `scope` fixed to `location` with a composite foreign key to `(id, scope)`: a role can't hold a tenant permission.
- `auth.user_tenant_permissions (user_id, tenant_id, permission_id, scope fixed 'tenant')`: unique per user, tenant and permission.
- `auth.tenant_owners (tenant_id PRIMARY KEY, user_id UNIQUE)`: one owner per tenant, one tenant per owner. Lives in `auth` because `tenancy` is created before `auth.users`.
- Trigger on `tenancy.locations` insert: give the tenant's owner the superadmin role at the new location. It is plpgsql because roles are seeded after the schema.
- `auth.platform_admins (id, email, password_hash, ...)`: their own credentials, never in `auth.users`, so the platform login can't sign in to a tenant and the reverse.
- `auth.has_tenant_permission(p_tenant_id, p_resource, p_action)` and `auth.current_tenant_id()`: read the grants live.
- `auth.is_platform_admin()`: true when the request set `app.platform_admin_id`.

**RLS (`0005`/`0007`)**
- `tenancy.tenants`, `tenancy.locations`, `tenancy.tenant_stripe_accounts`: writes need `auth.has_tenant_permission(...)` for the row's tenant. This replaces today's "superadmin at any location of the tenant" policies.
- Platform admins may read `tenants`, `tenant_stripe_accounts`, the count of `locations` and `tenant_invites`, and may update `tenants.is_active`. No other tenant table.

**Seeds**
- Tenant permissions: `tenant_settings r/u`, `tenant_locations c/r/u`, `tenant_stripe_account r/u`, `tenant_domains r/u`.
- The location-scoped `stripe_account u` grants are removed. `stripe_account r` stays for admins and superadmins: the location admin's payments page becomes a read-only status, so they can see why bookings are refused.
- Dev: `sa1user@test.com` becomes tenant 1's owner. Tenant 2 gets an owner too, for isolation tests. One dev platform admin.

## 3. Token and request context

```
claims: user_id, tenant_id, location_id | null,
        roles, permissions          (location; names unchanged)
        tenant_permissions          ({resource: [actions]}; {} for nearly everyone)
        email, first_name, iss, iat, nbf, exp, aud
```

- `get_current_token_context`: decodes the token, then requires the token's `tenant_id` to be the request host's tenant.
- `require_permission`: unchanged rule; a token without a location has no location permissions, so it gets 403.
- `require_tenant_permission(resource, action)`: checks `tenant_permissions`; ignores the location.
- `get_rls_db`: sets `app.user_id`, `app.tenant_id`, and `app.location_id` (empty when there is none).
- `/auth/v1/session`: location optional; adds the tenant permissions, so the account menu can show "Business settings".
- One helper issues every token (location login, business login, switching location), so the claims can't drift.
- **Host:** same-origin GETs carry no `Origin` header, so the tenant comes from the `Host` header, which Google's load balancer passes through unchanged (in dev, Vite's proxy keeps it). Unknown hosts get 404. Absolute links (emails, Stripe return URLs) are built from the tenant's stored hosts, never the raw header.
- **CSRF:** with `ssr = false`, SvelteKit's own check doesn't cover the API, so state-changing requests must carry an `Origin` that matches `Host`. With `SameSite=Lax` and host-only cookies, that covers the login, switching and registration endpoints too.
- **Platform token:** a different audience, so it fails every tenant and location dependency, and a tenant token fails the platform one.

## 4. Endpoints

| Endpoint | Permission | Why |
|---|---|---|
| `POST /auth/v1/business/login` | none (login) | Tenant from the host; refuses users without tenant permissions there; token has no location. |
| `POST /auth/v1/switch-location/{location_code}` | a valid token | Location must be in the token's tenant and the user must have a role there; reissues the cookie with that location's permissions and the current tenant permissions. |
| `GET /business/v1/overview` | `tenant_settings r` | Checklist: locations, Stripe, details, domain. |
| `GET/PATCH /business/v1/settings` | `tenant_settings r/u` | Business name, legal name, ABN, contacts, introduction, logo. |
| `GET/POST/PATCH /business/v1/locations` | `tenant_locations r/c/u` | List, add and edit locations (name, code, address, timezone, contact). The trigger makes the owner superadmin at a new one. |
| Stripe Connect routes (existing) | `tenant_stripe_account r/u` | Same service, keyed by `ctx.tenant_id` instead of the location's tenant. |
| `GET /stripe-account/v1/status` (location admin) | `stripe_account r` | Read-only, so a location's admins can see whether it can take payments. |
| `GET/PUT/DELETE /business/v1/domain` | `tenant_domains r/u` | Stage 6. |
| `POST /platform/v1/login` | none (login) | Platform admins only; platform audience. |
| `GET /platform/v1/tenants`, `PATCH /platform/v1/tenants/{id}` | platform admin | List with Stripe status and location count; deactivate. |
| `POST /platform/v1/invites` | platform admin | One-time link, emailed (add the email to `docs/email-policy.md` first). |
| `GET /registration/v1/invites/{token}`, `POST /registration/v1/register` | the invite token | Creates the tenant, its owner, the owner's tenant permissions and the `tenant_owners` row in one transaction; marks the invite used. |

## 5. Screens

- **`/business`** (tenant hosts): login; overview checklist; Locations (list, add, "Manage centre" switches and goes to `/{code}/admin`); Payments (Stripe Connect, moved from `/{location}/admin/payments`); Settings; Domain (stage 6). The location account menu shows "Business settings" to holders of tenant permissions.
- **`/`** (tenant hosts): the existing location cards, plus the business name, introduction and contact details from settings. No link to `/business`.
- **Platform host** (same SvelteKit app, decided by host): `/register?invite=…`, `/platform/login`, `/platform` (tenants, invites).

## 6. Build stages

Each stage ends with a dev rebuild and a test run.

1. **Same-origin API and tenant binding:** Vite proxies `/api` to the backend; the frontend calls `/api`; the tenant comes from the forwarded host; tokens carry `tenant_id` and it's checked; location becomes optional; `get_rls_db` sets the tenant; `SameSite=Lax`. Tests: a token from tenant 1 is refused on tenant 2's host.
2. **Tenant permissions:** scope column, `user_tenant_permissions`, `tenant_owners`, the location-insert trigger, reserved codes, `has_tenant_permission`, tenancy RLS rewritten, seeds; `tenant_permissions` in the token; `require_tenant_permission`.
3. **`/business`:** business login, switching location, overview, locations, settings, Stripe moved over (location admin page read-only).
4. **Platform owner and registration:** `platform_admins`, invites, registration, the console.
5. **Landing page:** business details on `/`.
6. **Custom domains:** see section 7.

## 7. Custom domains (stage 6)

Researched 23 October 2026 against Google Cloud, Stripe, Caddy, Cloudflare and AWS documentation. Prices for the load balancer are estimates; check them in the GCP calculator for australia-southeast1.

**Choice: a regional external Application Load Balancer in Sydney with Google-managed certificates (Certificate Manager).**
- TLS ends in australia-southeast1 only. The global load balancer and Cloudflare end TLS at the edge nearest the visitor, which can be overseas (a parent travelling): a data-residency question we avoid.
- Cloud Run domain mappings are ruled out: preview only, not offered in Sydney, and each domain needs Search Console verification.
- The load balancer sends every host to Cloud Run (serverless NEG; Cloud Run ingress limited to the load balancer). A reserved static IPv4 address, never released, because bare-domain tenants point an A record at it.
- One wildcard certificate covers every generated host (`*.<platform>.com.au`); each custom domain gets its own certificate (the domain plus `www`). The first 100 certificates are free.
- **Limit:** 100 certificates per load balancer proxy and per region. Only tenants with a custom domain use one. Before about 90, ask Google to raise it; if they won't, move to two Caddy VMs in Sydney with on-demand TLS (its `ask` endpoint returns 200 only for verified domains).

**What the tenant adds in DNS** (the app shows the exact values). A subdomain such as `book.after3.com.au` is recommended, since most businesses already have a website on their bare domain.
1. TXT `_<platform>-verify.<host>` = a token for this tenant and domain: proves *which tenant* owns it (the certificate record only proves it points at our project).
2. CNAME `_acme-challenge_<id>.<host>` → the value Certificate Manager returns. Permanent (renewals use it); nothing else at that name.
3. The host itself: a CNAME to `edge.<platform>.com.au` (ours, pointing at the static IP), or for a bare domain an A record to the static IP, with `www` as a CNAME.

**Data:** a `tenancy.tenant_domains` row per domain (hostname normalised and unique across tenants while not failed or removed; the platform's own domains refused), with its state, TXT token, Google's authorization and certificate names, a failure reason, and timestamps.

**States**, moved on by a background job polling with backoff:

| State | Moves on when |
|---|---|
| `pending_dns` | Created: hostname checked, token made, DNS authorization created, all three records shown. |
| `verifying` | The TXT record is found (public resolvers). Fails after 7 days. |
| `issuing_cert` | Certificate requested; done when Google reports it active. |
| `attaching` | Certificate added to the proxy's list (a whole-list replace, so one at a time). |
| `awaiting_routing` | The host resolves to us and `https://<host>/api/health` answers for this tenant. |
| `active` | It becomes the tenant's main host. Re-checked daily (TXT and certificate); a missing TXT for several days suspends it and emails the owner. |
| `failed` / `removing` | Reason stored, tenant can retry / detach, delete the certificate, then the authorization. |

**Redirects:** each tenant has one main host: its custom domain once active, otherwise the generated host. Page loads on the others get a 301 to it; `/api` is never redirected. The generated host keeps working as a fallback. Moving hosts logs people out once (cookies are per host). No HSTS `includeSubDomains` on domains we don't own.

**Stripe:** webhooks and the Connect OAuth callback stay on one platform host (`https://<platform>.com.au/api/...`). Checkout and onboarding return URLs aren't allowlisted by Stripe; `location_site_url` already checks them against the tenant's hosts, and must read them from `tenant_domains` once that table exists. Apple Pay and Google Pay domain registration (per connected account) is only needed if we leave hosted Checkout.

**Email:** stays on the platform's sending domain with the business's name as the sender name (`"After 3" <no-reply@mail.<platform>.com.au>`) and the business's address as reply-to. Sending from a tenant's own domain (SES identity in Sydney, three DKIM CNAMEs, optional MAIL FROM) is deferred.

**Open risks:** whether Google raises the certificate limit; load balancer cost; tenants breaking renewal by editing the `_acme-challenge` record (the daily check catches it); concurrent edits of the proxy's certificate list; which Australian DNS hosts support ALIAS records at the bare domain (assume none, hence the A record).
