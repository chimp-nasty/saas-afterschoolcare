# Job 06: External integrations, webhooks and recovery

Follow AGENTS.md and audit/SHARED.md. Read-only. Inspect all implemented integrations, not only Stripe.

## Check

- Stripe Connect ownership/account context, server-derived amounts/currency, OAuth state and return destinations, Checkout Sessions, refunds, receipt access and account revocation/replacement.
- Webhook raw-body verification, endpoint secrets/configuration references, event/account/object binding, metadata trust, supported event types and acknowledgement/transaction semantics.
- Repeated, concurrent and out-of-order delivery; delayed payment methods; local lookup misses; event received before local commit; external success after local failure; unknown versus failed outcomes.
- Reconciliation, replay/resumption, timeouts, retries, backoff, idempotency scope and durable state for manual resolution. Check recovery without a browser returning and after provider retry windows end.
- Email queueing versus durable delivery, after-commit behaviour, duplicate/lost messages, recipient resolution, permitted sensitive content and failure logging. Inspect SES event authenticity and suppression/status effects.
- Storage upload/download/delete boundaries, failed completion, orphaned objects, retry safety, retention and links. Follow the storage implementation and configuration actually used.
- Other integrations or background mechanisms discovered in the surface map, including third-party URL trust and blocking network calls.

## Adversarial scenarios

Wrong connected account sends a valid event; duplicate success races a retry; failure arrives after success; provider succeeds while local commit fails; webhook is down past hold expiry; account access is revoked; email/storage effect succeeds but the response is lost.

## Deliver

Use SHARED.md. Review docs/codex-findings/ for prior reports and distinguish new evidence from duplicates. Do not assume an issue is technically fixed because its discussion was closed. Verify current provider behaviour against primary documentation when needed; source code does not prove runtime delivery. Do not call Stripe, replay events or send emails without separate authorisation.
