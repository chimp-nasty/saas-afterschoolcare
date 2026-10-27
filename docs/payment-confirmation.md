# Payment confirmation without depending on webhooks

**Status: built 28 October 2026 (ideas 1–3, and the logging part of 4). Alerting is still to do, with monitoring.**

## The problem

A booking used to be marked paid only when Stripe's webhook arrived (`checkout.session.completed`). If an environment had no endpoints, the wrong signing secret (e.g. the `unset` placeholders from the deploy runbook), or Stripe couldn't reach the API, the family paid and their booking never became paid: Stripe had the money, our database didn't know. Worse:

- Cancelling saw the session was complete and refused with "already paid", leaving it to a webhook that never came.
- "Continue to payment" only reused an *open* session, so a completed one fell through to a brand new checkout: the family could pay twice.
- Missed events aren't replayed by `stripe listen` (local dev), so it never recovered there. Stripe retries deliveries for up to 3 days in production, but a pending booking only holds its place for 60 minutes (`booking_hold_lapsed`, schema 0009).

## What's built

All of it settles through one place, `PaymentSettlementService` (`app/integrations/payments/stripe/settlement.py`), which the webhook uses too. Settling locks the payment attempt and only moves a PENDING one, so whichever path gets there first wins and the rest change nothing (one confirmation email).

1. **Refuse checkout while payments can't be confirmed.** If the webhook secret for the endpoint a payment's events would arrive on is empty or not a real `whsec_...` secret (e.g. `unset`), booking is refused with 503 before the family is sent to Stripe (`webhooks_configured` in `client.py`).
2. **Confirm on sight.** Whenever we ask Stripe about a checkout and it says it's paid, it's settled there and then, on a transaction of its own, so it stays settled even when the request is then refused:
   - the success page (`GET /booking/v1/checkout/{session}`); if Stripe can't be reached it shows what we know
   - cancelling a pending group: refused with "already paid", but the booking is now confirmed
   - continuing to payment, or sending the same booking again: never opens a second checkout
   - a completed checkout still waiting on a delayed method (bank debit) can't be paid again or cancelled: 409 "still processing"
3. **Reconcile in the background.** `POST /internal/v1/payment-check` (Cloud Scheduler every 5 minutes, `X-Payment-Check-Secret`, deploy runbook step 11) asks Stripe about every pending attempt and settles those it has finished with, paid or expired. This catches families who closed the tab, and webhook outages, well inside the 60 minute hold. The list comes from `public.pending_checkouts()` (schema 0004), which answers only the `payment_check` channel; each attempt is then settled acting as its family, as the webhook does.
4. **Notice failures.** A payment settled without its webhook logs `stripe_payment_reconciled` (warning), and money taken for bookings already released logs `stripe_paid_without_bookings` (error, a refund is needed). Alerting on these and on webhook signature failures comes with monitoring.

Not built: asking Stripe (`WebhookEndpoint.list`) that both endpoints exist and listen for the right events. The secret check catches the misconfiguration seen in deployed dev; the payment check covers the rest.

Tests: `backend/tests/test_payment_confirmation.py`.
