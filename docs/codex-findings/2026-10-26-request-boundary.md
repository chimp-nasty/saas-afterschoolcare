# Job 01: Request boundary and exposed surface

- Audit date: 2026-10-26 (Australia/Brisbane).
- Status: Open; two Medium security findings confirmed by static inspection, not runtime reproduction.
- Scope: audit/01-request-boundary.md, following audit/SHARED.md and AGENTS.md.
- Revision: main, HEAD 7b01248 (`stage 5 implemented, business infra - add logo, favicon etc`), plus relevant working-tree and untracked changes. Deployment and custom-domain code were actively changing; this is not an immutable snapshot of that work.
- Disposition: Prioritised remediation required for the two Medium findings. No new Critical or High finding was confirmed in this pass. This is not a backend security clearance.
- Authorisation: The user approved saving this report after its terminal presentation and instructed the auditor to stop. Job 02 was not started. Saving this document does not authorise implementation or database/test operations.

## Summary

The request limiter trusts an attacker-controlled forwarding-header value and stores an unbounded number of buckets indexed by raw request paths. These are separate defects: fixing client-IP trust does not prevent unique paths from growing memory, and bounding memory does not establish a trustworthy client identity.

## F1 — [Medium] Client-controlled forwarding headers bypass throttling

### Evidence and triggering sequence

`backend/app/middleware/rate_limit.py:105` defines `_get_client_ip`. At line 109 it reads the raw `X-Forwarded-For` header; at line 114 it returns the first comma-separated value without establishing a trusted proxy chain. At line 58, the resulting value becomes part of the bucket key.

An anonymous HTTP client can repeatedly request the same login or password-reset endpoint with a different first forwarding-header value on each request. Every supplied value obtains a fresh allowance despite requests originating from the same client. A non-browser client can also supply the matching Origin required by the browser-write middleware; Origin validation is not intended to authenticate non-browser callers.

The deployment Dockerfile enables Uvicorn proxy headers and trusts forwarded peers, but the limiter independently reads the raw header. Restricting Cloud Run ingress to a load balancer does not itself make the first value trustworthy. Google documents that its external Application Load Balancer preserves supplied values and appends client/load-balancer addresses, explicitly warning that earlier values are unverified. No header replacement was found in the deployment source inspected.

Source: [Google forwarding-header behaviour](https://docs.cloud.google.com/load-balancing/docs/https#x-forwarded-for_header), consulted during the audit. Actual deployed header transformations were not inspected.

### Impact and severity

The attacker can bypass intended request restrictions on password guessing, reset-email requests and expensive authentication work. Password verification and endpoint-specific checks remain; this finding does not demonstrate account takeover or bypass every kiosk PIN lock. Medium reflects a practical bypass of an exposed abuse control with meaningful but bounded demonstrated impact.

### Existing safeguards

- Matching-Origin checks protect browser write flows, but do not prevent a non-browser attacker choosing headers.
- Per-path limits reject excess requests when a stable bucket identity is used.
- Endpoint credentials, permissions and database rules still apply.
- Some kiosk operations have separate PIN locks in SQL; do not assume this flaw bypasses them.

### Focused remediation

Define and enforce a single trusted client-address contract at ingress. Strip/replace client-provided forwarding values at the verified edge, or derive client identity from a validated proxy chain appropriate to the actual topology. Ensure untrusted direct callers cannot inject the trusted identity. Do not substitute another raw client-supplied header or blindly select a fixed header position without validating the topology.

If rate limits must apply across multiple workers/instances, address shared enforcement explicitly; correcting the header does not make process-local buckets global. That deployment consideration is separate from this confirmed bypass.

### Regression scenarios and acceptance criteria

- Repeated requests from one real client remain in the same applicable allowance when that client varies its supplied `X-Forwarded-For` prefix.
- Exercise a realistic load-balancer header chain, including client-supplied prefixes, multiple values, missing headers and malformed values.
- Untrusted direct traffic cannot nominate its own trusted client identity.
- Distinct legitimate clients remain distinguishable; shared kiosk traffic retains its intended allowance.
- The configured login/reset threshold is enforced after the proxy boundary, rather than only in a TestClient that directly chooses an identity.

## F2 — [Medium] Arbitrary paths permanently grow limiter memory

### Evidence and triggering sequence

`backend/app/middleware/rate_limit.py:40` creates an unbounded `defaultdict(deque)`. The bucket key combines client address and raw path at line 58; indexing that dictionary at line 61 creates an entry for each unseen key. Timestamp pruning at line 64 runs only when the same key is requested again, and dictionary keys are never evicted. Line 88 appends a timestamp before routing is completed.

An anonymous client can issue GET requests to `/api/nonexistent-1`, `/api/nonexistent-2`, and so on. Middleware allocates a new bucket before the router returns 404. GET requires no Origin, each distinct path gets its own allowance, and paths never revisited retain their deque and timestamps indefinitely. This does not require spoofing forwarding headers or possessing a valid tenant account.

### Impact and severity

Attacker-controlled requests create persistent process memory growth until restart. Continued traffic can exhaust an API process and disrupt service. Medium reflects service availability impact; no memory-exhaustion test was run and no exact request count, resource cost or deployed outage was measured.

### Existing safeguards

- A single bucket's timestamp queue is pruned when revisited, but this does not bound total key count.
- Per-path throttling limits repeated use of one key, but unique paths avoid that limit.
- A process restart clears state, but normal time-window expiry does not remove abandoned entries.
- No aggregate limiter or bounded bucket eviction was found in this implementation.

### Focused remediation

Bound total bucket storage and expire inactive buckets independently of another request to the same key. Avoid unlimited raw-path cardinality; consider route-level classes and an aggregate requester allowance, including unmatched routes. Choose eviction behaviour that does not simply reopen allowances under attack. Preserve legitimate endpoint-specific and kiosk behaviour.

Use a shared store if the intended policy must hold across multiple instances; a shared store must also bound key cardinality and expiration.

### Regression scenarios and acceptance criteria

- Many unique unmatched paths from one client cannot grow retained state without a defined bound.
- Inactive keys expire after the configured interval even if never revisited.
- Requests to many different paths still encounter an appropriate aggregate abuse limit.
- High-cardinality traffic cannot defeat throttling through repeated bucket eviction/recreation.
- Normal repeated-path limits and the shared-kiosk allowance continue working.
- Verify memory/state bounds in an isolated authorised test, not by load-testing a deployed care service.

## Other controls inspected

- Router composition, public/protected endpoint dependencies and exceptions, including the new `/api/internal/v1/domain-check` endpoint.
- Tenant-token binding to host-resolved tenant and platform endpoint host restrictions.
- Middleware registration and execution order, trailing-slash exemptions and handling before route execution.
- Origin checks for browser writes; webhook signature checks remain separate from those exemptions.
- The domain-check exemption requires the platform host and a constant-time shared-secret comparison (`backend/app/tenancy/routes/domain_check.py:28`). The secret value was not read.
- Host-only, HTTP-only login cookies with Secure/Lax configuration defaults.
- Tenant host allowlisting for Stripe return destinations and signed OAuth state validation.
- Generic unexpected-error responses and field/message-only validation envelopes.
- Thread-pool dispatch of blocking Stripe/SES webhook processing.
- Upload endpoints pass signed storage capabilities rather than accepting file bytes as multipart application uploads.
- Deployment URL routing, ingress guidance and proxy-header launch settings, treated as source rather than runtime evidence.

## Concerns and verification questions, not confirmed findings

1. Webhook handlers read whole request bodies before signature verification (`backend/app/integrations/payments/stripe/router.py:30`, `backend/app/integrations/email/router.py:30`). No application body-size ceiling was found. Determine actual upstream limits and concurrent-request behaviour before assigning a deployed denial-of-service severity. File upload limits are not request-body limits for these endpoints.
2. `backend/app/middleware/same_origin.py:55` compares Origin netloc with Host but omits scheme. No standalone exploit was established under Secure/Lax cookie defaults. Review the eventual ingress scheme/header contract and add negative-path coverage as appropriate.
3. `backend/app/main.py:21` uses FastAPI's default documentation settings. Source load-balancer routing appears to send the root docs/OpenAPI paths to the frontend rather than the API. Actual public exposure was not verified; enabled API documentation alone is not evidence of a critical vulnerability.
4. Infrastructure is under active construction. Verify deployed ingress restrictions, header rewriting and direct-service reachability before treating the source configuration as an operational safeguard.

## Tests inspected and gaps

- `backend/tests/test_auth.py:127` checks that six requests from one fixed client produce five successes and one 429. It does not vary forwarded identity or paths.
- `backend/tests/factories.py:410` creates clients with distinct supplied `X-Forwarded-For` values to obtain distinct buckets. This is useful test isolation but does not test a trustworthy production client-IP boundary.
- `backend/tests/test_tenant_site.py` covers cross-tenant token refusal, unknown hosts, missing/wrong origins, webhook Origin exemptions and host-only cookies. It does not establish deployed proxy handling or cover the Origin scheme distinction.
- `backend/tests/test_domains.py` includes platform-host and shared-secret denial paths for domain checks. Tests were inspected only, not run.

## Coverage, known findings and limits

All job 01 checklist areas were inspected statically: route/dependency inventory; middleware/exemptions and alternate-path considerations; host/proxy handling; Origin/CORS/cookie controls; redirects; request bodies/parser surface/error handling; and rate-limit identity/topology. Coverage is complete for this declared source-review scope, not for live deployment verification, exhaustive parser fuzzing or load testing.

The earlier payment-recovery report and database-boundary observations were not reassessed or cleared in this job. Do not count them as new job 01 findings or assume that closing their discussion verified a fix.

No environment files were read. No tests, application startup, database commands, migrations, builds, scanners, live requests or load tests were executed. Public Google and FastAPI documentation was consulted to check proxy and middleware behaviour. The two confirmed findings are static source conclusions; no production exploitation was demonstrated. References may move as the working tree changes.

The audit stopped after this approved report was saved. Job 02 and subsequent jobs require the user's next instruction.
