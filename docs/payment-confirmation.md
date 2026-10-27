# Payment confirmation without depending on webhooks

**Status: backlog, noted 26 October 2026. Not agreed or built.**

## The problem

A booking is only marked paid when Stripe's webhook arrives (`checkout.session.completed`, handled in `app/integrations/payments/stripe/webhook.py`). Nothing checks that the webhooks are set up before a family is sent to Stripe. If an environment has no endpoints, the wrong signing secret (e.g. the `unset` placeholders from the deploy runbook), or Stripe can't reach the API, the family pays and their booking never becomes paid: Stripe has the money, our database doesn't know.

The same happens, more rarely, in production if a webhook delivery is delayed or the endpoint is down for a while.

## Ideas, in order of value

1. **Refuse checkout while payments can't be confirmed.** The API knows when its own setup is incomplete: a webhook secret missing or still a placeholder. Treat that like a tenant whose Stripe account can't take payments: bookings and checkouts are refused with a clear message, and Business settings › Payments says what's missing. A stronger version also asks Stripe (`WebhookEndpoint.list`) that both endpoints exist, are enabled, point at this environment and listen for the events we need, and records the result (on start-up, or from the platform console), so a misconfigured environment can't take money.
2. **Confirm on return.** When the family lands back on the success page, the API fetches that Checkout Session from Stripe (on the tenant's connected account) and settles it through the same `_settle` path the webhook uses. Settling is already safe to repeat, so whichever arrives first wins. Cards are then confirmed even with no webhooks; delayed payment methods and refunds still need them.
3. **Reconcile in the background.** A scheduled job (Cloud Scheduler, like the domain check) looks for payment attempts still pending after, say, 15 minutes and asks Stripe for each session's real state. This catches families who closed the tab before returning, and webhook outages.
4. **Notice failures.** Log (and later alert on) webhook signature failures and on attempts that the reconcile job had to settle, since either means the endpoint is wrong or unreachable.

1 stops the case seen in deployed dev; 2 and 3 make confirmation not depend on webhooks alone.
