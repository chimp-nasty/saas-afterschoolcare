# Short-lived access tokens with rotating refresh tokens

**Status:** Backlog, proposed 24 October 2026. Not planned and not built. Talk it through and agree it before building (as with every slice).

**Today:** one JWT access token in an HTTP-only cookie, valid for 90 minutes (`JWT_ACCESS_TOKEN_EXPIRE_MINUTES`), with no refresh. Taking away a role or permission reaches the token only when it expires: a known, accepted gap. Tenant permissions are already checked live by the database (`auth.has_tenant_permission`); location roles are not.

## Proposal

1. **Access tokens:** JWTs expiring after 5 minutes, renewed automatically without interrupting the user. They keep the same claims as now: user, tenant, optional location, roles, location and tenant permissions.
2. **Refresh tokens:**
   - A separate refresh token, rotated on every successful refresh, with the previous one invalidated.
   - The database keeps only hashes.
   - Reuse of an old refresh token is detected and revokes the whole session.
3. **Session lifetime:**
   - 24 hours by default, measured from login (absolute). Refreshing doesn't extend it; after it ends the user logs in again.
   - The access token and session lifetimes are settings.
4. **Security:**
   - Separate Secure, HttpOnly cookies with suitable SameSite values.
   - The refresh endpoint is protected against cross-site requests.
   - Rotation is atomic, and concurrent refreshes are handled safely.
   - Logout ends the refresh session.
5. **Frontend (SvelteKit):**
   - Silent renewal.
   - Expired access tokens handled gracefully, with no refresh loops.
   - A redirect to login when the session expires or is revoked.
6. **Compatibility:** authentication and authorisation behave as they do now. The permission model is unchanged, tenant and location isolation are kept, and every existing endpoint keeps working.
7. **Tests:**
   - access token expiry
   - refresh and rotation
   - reuse detection
   - concurrent refreshes
   - absolute session expiry
   - logout and revocation
   - tenant isolation and permissions preserved

## How it fits the current code (notes for when it's picked up)

- **One place issues tokens.** Every access token comes from `AuthService._issue_token` (location login, business login, switching location). Refreshing would call the same helper, so claims stay identical. Switching location would rotate within the same session rather than start a new one.
- **Roles and permissions are read again on refresh.** A refresh rebuilds the claims from the database, so removing a role or permission would take effect within the 5-minute access lifetime. That closes today's 90-minute gap.
- **Sessions table.** For example `auth.user_sessions`:
  - `id`, `user_id`, `tenant_id`
  - the current refresh token's hash
  - `expires_at` (absolute: login + 24 hours, never moved)
  - `revoked_at`, `created_at`

  Rotation is one conditional `UPDATE … WHERE refresh_hash = :old AND revoked_at IS NULL AND expires_at > now()`, which is atomic. Seeing an old hash again revokes the session.
- **Concurrent refreshes.** Two tabs refreshing at once would look like reuse. Common fixes:
  - a short grace window in which the just-replaced token still returns the new pair, or
  - the frontend sending a single refresh for all tabs, coordinated with a `BroadcastChannel` or a lock.

  Choose one when designing this.
- **Cookies and CSRF.** The API is already on each tenant's own site under `/api`, with host-only `SameSite=Lax` cookies and an `Origin` check on every change (`app/middleware/same_origin.py`). The refresh cookie can be limited to the refresh endpoint's path, so it isn't sent with any other request.
- **Frontend.** `apiWrapper` (`frontend/src/lib/api/wrapper.ts`) is the one place requests go through. On a 401 it would refresh once and retry once, then go to login, which prevents loops. The session-loading layouts (`[location_code]`, `business`) stay as they are.
- **Out of scope unless chosen:**
  - The platform console's token (`platform_token`) would need the same treatment or a decision to leave it.
  - Kiosk device cookies and the family kiosk's session tokens are separate mechanisms and are unaffected.
