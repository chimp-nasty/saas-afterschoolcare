# Stripe payment recovery after webhook outages

- Audit date: 2026-10-24 (Australia/Brisbane).
- Status: Open; confirmed by static inspection, not reproduced against a running system.
- Priority: Recommended release blocker because a completed payment can lead to another checkout or a lost booking without a resolved refund.
- Scope: Checkout creation/resumption, cancellation, payment status reads, webhook settlement, booking hold expiry, customer screens and relevant tests in the current working tree.
- Authorisation: The user approved this finding document after the audit was presented in the terminal. This document does not itself authorise implementation, database operations or test execution. Follow AGENTS.md and obtain the applicable authorisation before those operations.

## Reported behaviour and conclusion

The user reported that a Stripe Checkout Session completes while the webhook is unavailable, but the booking remains awaiting payment. Cancelling then reports that the booking is already paid, while the UI still offers checkout. Restarting the webhook receiver does not appear to recover the booking.

The code supports the contradictory state and exposes a second-payment path. Booking reads use local state; cancellation queries Stripe and refuses a completed session without reconciling local state. Checkout resumption does not apply the same completed-session safeguard.

A valid success event delivered while the original bookings are still pending should confirm them. The audit did not establish why the user's specific event was not delivered or processed after the receiver returned. Do not equate restarting a listener with replaying a missed event.

## Confirmed findings

### F1 — [High] Completed checkout can be replaced with another payable session

**Evidence:** `backend/app/public/services/bookings_create.py:334` (`_resume_checkout`) retrieves the latest attempt's Stripe session. At line 351 it returns the session only when its status is `open`. A `complete` session falls through to `_start_checkout`, just like an expired session. The group can still pass the local pending-state check because the success webhook has not arrived.

The new attempt receives a new UUID and therefore a new Stripe idempotency key (`backend/app/public/services/bookings_create.py:326`). Idempotency is per attempt, not per paid booking group. The constraints on `public.payment_attempts` in `backend/migrations/schema/0004_public.sql:1702` make Stripe session and PaymentIntent identifiers unique but do not prohibit separate successful charges for one group.

**Trigger:** Pay on Stripe, withhold the completion webhook, then continue checkout before the local hold expires.

**Impact:** The family can pay a second time for the same booking. Hiding the button alone would leave the backend defect reachable.

**Existing safeguards:** Open sessions are reused; locally confirmed groups are refused; server-derived booking snapshots determine prices; calls use the attempt's connected account. These do not cover completed payment with stale local state.

**Remediation:** Handle completed checkout explicitly. Never create a replacement checkout for a session whose payment succeeded or is still processing. Reconcile verified Stripe state through a shared settlement operation. Distinguish session `status` from `payment_status`: completion alone is not proof of settled funds for delayed payment methods. `StripeCheckout` currently exposes session status but not payment status (`backend/app/integrations/payments/stripe/client.py:27`).

### F2 — [High] Unresolved payments have no application reconciliation path

**Evidence:** `backend/app/public/services/bookings_read.py:132` (`get_checkout_status`) reads the stored attempt and returns its local status at line 154. It does not retrieve Stripe state. `backend/app/public/services/bookings_update.py:80` detects completed checkout during cancellation but raises `BookingGroupAlreadyPaidError` without settling the attempt or bookings. The transaction rolls back when the error is raised.

The success page polls local status ten times at two-second intervals and then stops (`frontend/src/routes/[location_code]/(customer)/bookings/success/+page.svelte:22`). No application payment-reconciliation scheduler or recovery workflow was found in the inspected application. `infra/stripe/README.md:52` also describes webhook-only recording of paid checkouts.

**Trigger:** Stripe accepts payment, but the success event never reaches a successful settlement transaction.

**Impact:** Browser refreshes and cancellation do not repair local state. The family has paid but lacks a confirmed booking, including inclusion in workflows that require confirmed bookings. The success screen can continue to say payment is being confirmed after polling stops.

**Existing safeguards:** Webhooks verify signatures, select the recorded connected account, and apply RLS identity/location context. Cancellation's refusal prevents releasing a completed checkout as an ordinary unpaid cancellation. Those protections should be retained.

**Remediation:** Add server-side reconciliation for unresolved attempts against their recorded Stripe account and Checkout Session. Share an idempotent settlement operation between webhook processing and reconciliation. Recovery must work without a browser returning. A customer-triggered refresh can improve responsiveness, but is not a substitute for unattended recovery. Do not trust redirect query parameters as payment evidence.

### F3 — [High] Paid places can expire, with recovery reduced to a log message

**Evidence:** `backend/migrations/schema/0009_pending_booking_hold.sql:28` treats a pending booking older than 60 minutes as lapsed without checking Stripe. Reads expose it as expired; capacity calculations stop counting it. At line 161, the booking-rule trigger persists the expiry when another booking is made for that service day.

`backend/app/public/repositories/booking.py:399` (`settle_pending_for_group`) updates only rows whose stored booking status is still `PENDING` (line 423). If a delayed success event arrives after the rows were swept to expired, `backend/app/integrations/payments/stripe/webhook.py:233` logs `refund_required` and returns. The payment attempt is already marked successful. The transaction commits and the endpoint acknowledges delivery, but no refund or durable resolution task is created. Repeated events skip the successful attempt at line 202.

**Trigger:** Payment completes during the hold, its webhook is delayed beyond 60 minutes from booking creation, another successful booking takes the released capacity, and the original success event arrives later.

**Impact:** A paid family loses its booking and retains a charge that the application has not resolved. Returning the webhook to service does not repair this case automatically. With multiple service days, also assess partial settlement: the handler checks only whether zero bookings were confirmed.

**Existing safeguards:** Expiry prevents abandoned unpaid sessions from holding capacity forever. Settlement avoids blindly resurrecting swept bookings, which could overbook the day. Preserve both protections while resolving money actually received.

**Remediation:** Coordinate hold expiry and reconciliation so unknown payment state is not silently treated as proof of non-payment. When capacity has already been reassigned, persist a recoverable exception and an idempotent refund or explicit operator-resolution workflow. Do not unconditionally reconfirm expired bookings or rely solely on logs.

## Recommended implementation direction

Keep the current route/service/repository boundaries. Put transaction ownership and recovery orchestration in services, queries and locking in repositories, and capacity/integrity rules in SQL.

Use one settlement operation for verified payment evidence, callable from webhooks and reconciliation. Serialize competing settlement, checkout resumption and cancellation for a group. Make repeated or concurrent calls safe, including recovery after a process crash. Preserve connected-account ownership, server-derived amount/currency checks, RLS context across transaction boundaries, and protection against processing the wrong session/attempt.

Represent payment success separately from booking fulfilment: a successful charge does not imply all booking places were confirmed. Give unresolved outcomes durable state and an operational route to resolution. Change customer messaging to distinguish payment processing, confirmed booking, and payment received with a booking problem. Keep replacement checkout unavailable while a previous payment is successful or unresolved.

These are outcome requirements, not a mandate for a broad rewrite or a particular queue/scheduler product.

## Regression scenarios and acceptance criteria

1. Complete a session in the fake Stripe provider without delivering its webhook. Continuing checkout must not create another session or charge; cancellation must not leave the UI offering another payment.
2. Run reconciliation without a customer return. Verified paid attempts must converge to confirmed bookings when their places remain valid.
3. Deliver the webhook after reconciliation, and reconcile after webhook delivery. Both orders must result in one settlement and no duplicate refund or confirmation side effects. Exercise concurrent calls, not only sequential duplicates.
4. Leave a completed session unpaid while a delayed method processes. Do not confirm it as paid or create another payable session. Later success/failure must resolve consistently.
5. Make Stripe temporarily unreachable. Do not infer payment failure, release paid capacity through an unsafe recovery action, or create a replacement checkout merely because verification failed. Record/retry the unresolved outcome.
6. Delay a successful payment event beyond hold expiry and reassign capacity. The original payment must produce a durable fulfilment exception and a recoverable refund/resolution path; it must not overbook or disappear into logs.
7. Exercise partial group expiry across multiple service days. Every charged line must be either fulfilled or accounted for in a durable resolution, rather than treating any nonzero confirmation count as complete success.
8. Restart during reconciliation/refund processing and retry. Recovery must resume without duplicate charges/refunds or loss of unresolved work.
9. Verify customer, tenant, location and connected-account isolation for status refresh and recovery. Do not allow a supplied session ID to reconcile another family's payment.
10. After bounded browser polling ends, show an accurate unresolved state with an appropriate refresh/support path. After recovery, booking lists, review, success page and operational views must agree.

## Tests inspected and coverage gaps

- `backend/tests/test_checkout.py`: webhook confirmation, repeated deliveries, delayed-method success, open-session reuse and replacement after expiry.
- `backend/tests/test_booking_review.py:94`: rejects another checkout only after the success webhook has already settled the group; it does not cover completion on Stripe with the webhook withheld.
- `backend/tests/test_booking_review.py:158`: explicitly expects cancellation to be refused while local booking state remains pending after Stripe completion.
- `backend/tests/test_booking_review.py:252`: explicitly accepts successful payment with expired bookings after the place was reassigned. Logging that a refund is needed is not a complete recovery assertion.

Existing tests demonstrate parts of the current behaviour; their presence does not establish an acceptable end-to-end outcome. Extend or revise their assertions as part of an authorised fix.

## Runtime evidence still needed

- Was the outage a stopped local `stripe listen` process, an unavailable registered endpoint, or a handler failure?
- For the affected event, what destination/account, delivery times and HTTP responses were recorded? Did it reach `/api/v1/webhooks/stripe/connect` with the expected signing configuration?
- Did the payment attempt remain pending, become successful, or become failed? Were booking rows still pending, only effectively expired, or persisted as expired?
- Were multiple attempts or charges created for the same group? Did another booking take its capacity?

Do not read `.env` files or expose secrets to answer these questions. Runtime inspection and any recovery actions require their own applicable authorisation.

Stripe documents scheduled retries for registered endpoints: up to three days in live mode and three retries over several hours in a sandbox. Resuming a receiver is not proof that the missed event has been redelivered. See [Stripe webhook delivery behaviour](https://docs.stripe.com/webhooks#automatic-retries). The user's particular non-recovery cause remains unverified.

## Verification limits

The audit used static source, SQL and test inspection plus official Stripe documentation. No application startup, database queries, migrations, rebuilds, backend tests, Stripe API calls or event replays were performed. No application code was changed. Source schema does not prove deployed database state. Line references were taken from the working tree and may move during implementation; use the named methods/tests to relocate them.
