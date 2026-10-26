# Job 00: Backend surface and trust map

Follow AGENTS.md and audit/SHARED.md. This is a read-only reconnaissance and scoping job, not an implementation task. Present the map in the terminal; do not create inventory files.

## Objective

Identify what can enter the backend, what must be protected and which components enforce trust. Establish a useful scope for later jobs rather than assuming that all sensitive behaviour is in routes or Stripe code.

## Inspect

- Application/router composition, middleware, dependencies, startup hooks, scheduled/background work, webhooks and operational entry points. Include routes outside the usual API envelope and unauthenticated endpoints.
- Identity paths: anonymous visitor, family/customer, staff/admin/superadmin, tenant owner, platform admin, paired kiosk, provider webhook and trusted server code.
- Assets: credentials/tokens, child and health data, pickup permissions, attendance, documents, booking capacity, prices, payments/refunds, email and tenant configuration.
- Boundaries: browser/proxy/API, host/tenant, identity/location, API/database role and RLS, server/storage, server/provider, cache/process and asynchronous delivery.
- Database owners/runtime roles, SECURITY DEFINER functions, seed permissions and migrations that replace earlier functions or policies. Do not infer deployed schema from source.
- Relevant infra and dependency manifests. Do not open environment files.

## Deliver

A concise entry-point and trust-boundary map, the highest-value flows for jobs 01-07, and any confirmed findings using SHARED.md. Identify missing deployment/runtime evidence and likely blind spots. Mapping alone is not a security clearance; list areas not yet audited. Later jobs may reconstruct their own relevant map without requiring this job to have a saved report.
