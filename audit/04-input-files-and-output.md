# Job 04: Input handling, files and output safety

Follow AGENTS.md and audit/SHARED.md. Read-only. Follow untrusted values to their actual sinks.

## Check

- Raw/dynamic SQL, identifier interpolation, command/process execution, deserialisation, template evaluation and dynamic imports where input can influence behaviour. Parameterised SQL is a safeguard; string construction alone is not proof of injection.
- Outbound HTTP/URL fetching, redirects, allowed destinations, DNS/private-network reachability and provider-supplied URLs. Identify SSRF only where the server actually fetches an influenced destination.
- Upload ownership, file keys/paths, traversal, validation beyond claimed MIME/extension, size limits, decompression/pixel limits and parser errors. Examine pending-upload/finish/download/delete sequences and races.
- Signed URL scope, expiry, object ownership, public/private storage choices, cache headers, content disposition/type and sensitive documents exposed through public routes or storage configuration.
- Persisted user/staff text rendered in browser HTML, rich content, email templates, headers and logs. Follow relevant frontend rendering when required to establish exploitability; do not assume framework escaping is absent.
- Schema field bounds, extra fields, coercion, Unicode/canonicalisation, malformed IDs/dates and expensive validation. Connect a validation gap to a practical security or integrity consequence.

## Adversarial scenarios

Cross-owner object key, forged upload completion, unexpected file content, oversized/decompression input, stored script payload reaching an unsafe renderer, attacker-controlled fetch destination and invalid values that reach dynamic SQL or process arguments.

## Deliver

Use SHARED.md. Name each source, sink and escaping/validation control inspected. Do not generate malicious files, fetch private addresses, upload artifacts or run exploit payloads without separate authorisation.
