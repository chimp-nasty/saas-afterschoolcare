# Job 01: Request boundary and exposed surface

Follow AGENTS.md and audit/SHARED.md. Audit the current backend HTTP boundary, following routes, middleware and proxy/deployment configuration as needed. Read-only.

## Check

- Inventory registered routes, methods, public/admin/debug/health/docs endpoints and aliases. Verify router-level and endpoint-level dependencies rather than relying on names or comments.
- Middleware execution order, exception paths, rate-limit and CSRF exemptions, path normalisation/trailing slashes and webhook exceptions. Check whether alternate paths or methods bypass controls.
- Host-to-tenant resolution, custom hosts, inactive tenants, trusted forwarded headers, scheme/port interpretation and proxy assumptions. Separate documented proxy behaviour from configured or verified behaviour.
- Origin checks, CORS, cookie attributes and CSRF for all state-changing browser flows, including login, switching and registration. Assess GET endpoints that change state on their merits, including validated provider callbacks.
- Absolute URL construction, return/cancel links, redirects and trusted destinations. Check malformed inputs and whether stored or request-provided hosts can escape tenant binding.
- Body size, multipart/parser limits, malformed payload handling, information in errors, debug tracebacks and synchronous/blocking work on asynchronous request paths.
- Rate-limit identity keys and deployment topology; assess realistic bypass and legitimate shared kiosk traffic. Deep resource exhaustion analysis belongs in job 07, but follow demonstrated boundary bypasses here.

## Adversarial scenarios

Anonymous calls, unknown/wrong tenant hosts, forged forwarding headers where accepted, missing/null/mismatched origins, alternate route spellings, invalid content types and exceptions before endpoint execution. Do not send live requests without separate authorisation.

## Deliver

Use SHARED.md's output and severity rubric. Explain reachable bypasses and actual impact. Do not equate an absent header/control with a vulnerability when another verified control closes the path.
