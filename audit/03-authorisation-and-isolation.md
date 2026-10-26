# Job 03: Authorisation, ownership and database isolation

Follow AGENTS.md and audit/SHARED.md. Read-only. Trace authorisation from endpoint to SQL; UI visibility is not enforcement.

## Check

- Endpoint permissions and object ownership for reads, lists, writes, bulk operations, exports and linked resources. Check guessed IDs, nested IDs, filters, pagination and cross-owner references.
- Tenant, location and family separation; location versus tenant permissions; platform versus tenant identities; staff web versus kiosk channel; device versus staff identity at a kiosk.
- Optional location sessions, token-to-host binding, switching and stale token claims. Establish which permissions are checked live and which are token snapshots.
- Database RLS activation/forcing, grants, runtime role privileges, broad policies, missing policies and helpers replaced in later schema files. Follow reads and writes separately.
- Transaction-local context across service calls, commits/rollbacks, lazy loads, trusted server paths and pooled connections. Check unset context semantics rather than assuming unset always denies access.
- SECURITY DEFINER functions, EXECUTE privileges, ownership/search paths, untrusted parameters and validation of cross-owner references. Evaluate SQL functions as entry points, not only as implementation details.
- Mass assignment and updates to protected columns, including identity, ownership, platform-only state and staff-only fields. Inspect schemas, repositories, constraints and triggers together.

## Adversarial scenarios

Family A targets family B; tenant A targets tenant B; same user holds roles at two locations; staff uses a web route to seek kiosk-only powers; device substitutes a staff identity; platform credentials are used on tenant paths; direct app-role operations probe claimed database invariants.

## Deliver

Use SHARED.md. Explicitly distinguish reachable API vulnerabilities from database defence-in-depth gaps. Give the minimum identity/access prerequisites and the safeguards checked before asserting an authorisation failure.
