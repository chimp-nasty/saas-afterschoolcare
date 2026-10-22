# Stripe Connect setup

How payments reach each business. Every tenant has its own **Standard** connected Stripe account, and families pay it directly (**direct charges**): the centre is the seller, and owns payouts, disputes and its Stripe dashboard. The platform keeps only its own keys and each tenant's account id (`tenancy.tenant_stripe_accounts`). The app side is `backend/app/integrations/payments/stripe/` and Admin › Payments (`backend/app/tenancy/services/stripe_connect.py`).

Platform subscriptions (billing tenants for the software) are separate and done by hand for now.

Connected accounts and their onboarding links are created with Stripe's **Accounts v2** API (`/v2/core/accounts`, `/v2/core/account_links`), which Stripe requires for new Connect integrations: full dashboard, Stripe collects fees and carries losses, merchant configuration with card payments (the v2 equivalent of a Standard account). Everything else (checkouts, refunds, reading an account's flags, the `account.*` webhooks) uses v1, which works with v2 accounts. The installed SDK predates v2, so those two calls are plain HTTP in `StripeClient`; upgrading the SDK is a separate job.

## 1. Turn on Connect for the platform account (once, test and live)

In the Stripe dashboard of the platform's account:

1. **Settings → Connect → Get started.** Choose to onboard **Standard** accounts ("Sellers will collect payments directly"), with the platform **not** responsible for losses or fees on direct charges.
2. Complete the **platform profile** (what the platform does, who its users are).
3. **Settings → Connect → Branding:** the platform's name, icon and colour (shown during a centre's onboarding).
4. Do the same in **test mode** for dev (Connect settings are separate per mode).

## 1b. "Connect with Stripe" (linking a business's existing account)

A business that already has a Stripe account links it through Stripe's OAuth instead of making a new one (Admin › Payments → **Connect your Stripe account**). Stripe returns everyone to one address on the API, which sends them back to their own site.

1. **Settings → Connect → Onboarding options → OAuth:** turn on OAuth for Standard accounts.
2. Add the redirect URI `{API_BASE_URL}/stripe-account/v1/oauth/callback`, e.g. `https://api.<domain>/stripe-account/v1/oauth/callback` (and `http://localhost:8000/stripe-account/v1/oauth/callback` in test mode).
3. Copy the **client id** (`ca_…`, separate for test and live) into `STRIPE_CONNECT_CLIENT_ID`. Without it, only "Create a new Stripe account" is offered.

The business stays in control: it can remove the platform's access from its own Stripe dashboard at any time (bookings then close, see the table below).

## 2. Webhook endpoints (production)

Two endpoints on the API, both under **Developers → Webhooks**:

| Endpoint | Listens to | Events | Secret setting |
|---|---|---|---|
| `https://api.<domain>/api/v1/webhooks/stripe` | **Your account** | `checkout.session.completed`, `checkout.session.async_payment_succeeded`, `checkout.session.async_payment_failed`, `checkout.session.expired`, `refund.created`, `refund.updated`, `refund.failed` | `STRIPE_WEBHOOK_SECRET` |
| `https://api.<domain>/api/v1/webhooks/stripe/connect` | **Connected accounts** | the same, plus `account.updated` and `account.application.deauthorized` | `STRIPE_CONNECT_WEBHOOK_SECRET` |

With direct charges, a family's checkout and refunds happen in the centre's account, so they arrive on the **Connect** endpoint. The platform endpoint only settles payments made before an account was connected (seeded data). Each event is checked against the account the payment was made in.

## 3. Dev

1. Rebuild, log in as the superadmin (`sa1user@test.com`, password `123`) and open **Admin › Payments → Connect Stripe**. In test mode, Stripe's onboarding accepts test data ("Use test data" / phone `000 000 0000`, code `000000`).
2. Forward both kinds of events to the local API with the Stripe CLI ([install](https://docs.stripe.com/stripe-cli); `stripe login` once, into the platform's account). One command, in its own terminal, while the API runs:

   ```powershell
   stripe listen --forward-to localhost:8000/api/v1/webhooks/stripe --forward-connect-to localhost:8000/api/v1/webhooks/stripe/connect
   ```

   Your account's events go to the first endpoint and connected accounts' events (a family's checkout and refunds, `account.updated`) to the second. It prints one signing secret (`whsec_…`) for the session: put it in `backend/.env` as **both** `STRIPE_WEBHOOK_SECRET` and `STRIPE_CONNECT_WEBHOOK_SECRET`, then restart the API. The secret stays the same on later runs from the same machine, so this is needed once (until the CLI login expires, about 90 days). Each forwarded event and the API's response code is printed in that terminal; a `400` usually means the secret in `.env` doesn't match.

   Without the CLI, **Refresh status** on Admin › Payments reads the account's state from Stripe instead, but paid checkouts and refunds are only recorded through the webhook, so bookings stay pending.
3. Copy the connected account's id (`acct_…`, shown in your platform dashboard under **Connected accounts**) into `backend/.env` as `STRIPE_DEV_ACCOUNT_ID`. From then on, every rebuild links it to tenant1 again (`migrations/dev_seed/0005_dev_stripe_account.py`), so onboarding is only needed once.

## What each state means

| State (Admin › Payments) | Bookings | Refunds of past payments |
|---|---|---|
| Not connected, or onboarding unfinished | Closed | — |
| Taking bookings | Open | Through the account |
| Turned off in our app (Disconnect) | Closed | Still through the account |
| Access revoked by the business in Stripe | Closed | Only in their own Stripe dashboard |

## Production settings (Stripe)

| Setting | Value |
|---|---|
| `STRIPE_SECRET_KEY` | The platform's **live** secret key (`sk_live_…`), or better a restricted key with Connect, Checkout, refunds and accounts access |
| `STRIPE_WEBHOOK_SECRET` | The `whsec_…` of the **Your account** endpoint |
| `STRIPE_CONNECT_WEBHOOK_SECRET` | The `whsec_…` of the **Connected accounts** endpoint |
| `STRIPE_CONNECT_CLIENT_ID` | The live OAuth client id (`ca_…`) |
| `API_BASE_URL` | The API's public address, e.g. `https://api.<domain>` (no trailing slash) |
| `STRIPE_DEV_ACCOUNT_ID` | Not set (dev only) |
