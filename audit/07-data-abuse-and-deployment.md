# Job 07: Data protection, abuse resistance and deployment

Follow AGENTS.md and audit/SHARED.md. Read-only. Inspect source configuration and deployment definitions without reading environment files or claiming they match production.

## Check

- Response field minimisation, sensitive data in exceptions/logs/traces/emails, bearer links, health/child data and identity enumeration. Trace serializers and error handlers, not just schemas.
- Cache keys, lifetime, mutation/invalidation, tenant/user scoping, process-local assumptions and sensitive responses cached by browsers/proxies. Check which cached results bypass normal service checks.
- Retention, deletion, soft-delete visibility, document access after revocation, storage leftovers and implemented auditability/recovery. Separate stated policies from implemented enforcement.
- Pagination, unbounded collections, N+1 or expensive attacker-influenced queries, body/file sizes, CPU/memory-heavy parsing, outbound timeouts, thread/worker/connection exhaustion and request fan-out.
- Rate-limit storage and identity keys across workers/instances, spoofable client identifiers, shared kiosk traffic and expensive public endpoints. A small single-process limiter is not automatically exploitable without a realistic deployment/abuse path.
- Application/database least privilege, exposed management/debug surfaces, container user, image/build content, secret handling references, ingress/proxy/TLS configuration and backend-facing infrastructure. Never print secret values or read .env variants.
- Dependency manifests/lockfiles and known vulnerabilities using authoritative advisories. Establish declared/resolved version and reachable affected functionality; report uncertain installed/deployed versions explicitly. Do not install tools or invoke scanners without authorisation.

## Adversarial scenarios

Low-cost repeated public requests exhaust a bounded resource; one tenant receives another's cached response; deactivated/deleted content remains accessible; validation error leaks sensitive input; deployment configuration exposes a trusted-only path; a known affected dependency is reachable through actual application usage.

## Deliver

Use SHARED.md. Explain the exposure, cost/asymmetry and practical impact of abuse claims. Separate configuration evidence, documented intentions and unknown production settings. Avoid speculative legal/compliance conclusions; focus on implemented data protection and system behaviour.
