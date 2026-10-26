# Job 02: Identity, credentials and session lifecycle

Follow AGENTS.md and audit/SHARED.md. Read-only. Trace identity establishment and renewal, not only permission dependencies.

## Check

- Login and account creation across tenant, business, platform and kiosk identities. Inspect active-state checks, enumeration, timing/error distinctions, password hashing/verification and brute-force/lockout behaviour.
- JWT signing algorithms, keys/configuration references without reading secrets, issuer/audience/purpose checks, required claims, parsing, lifetime and error handling. Check whether identity types can be substituted for one another.
- Cookies and logout, password change/reset, account deactivation, role changes and token reissuance/switching. Determine precisely which changes invalidate existing sessions and which rely on a documented stale-token window.
- Invitations, pairing codes, PINs, reset tokens and other bearer capabilities: entropy, storage, expiry, binding, one-time consumption, replay, races and lockouts. Trace database enforcement.
- Recovery access: whether a user can gain or retain another identity through onboarding, reset, invite reuse or location switching. Assess legitimate multi-location/multi-role identities rather than assuming one role per person.
- Tokens/credentials in URLs, logs, errors, API responses, email and storage. Describe leaks without printing secret values.

## Adversarial scenarios

Valid token on the wrong site, expired or wrong-purpose token, deactivated user with an existing token, stolen/reused invite/reset code, concurrent capability use, repeated PIN attempts and a switch to a location without membership. These are static scenarios unless runtime verification is separately authorised.

## Deliver

Use SHARED.md. Separate proven takeovers/replay paths from assumptions about deployment settings and accepted revocation delays. State which invalidation events were traced end to end.
