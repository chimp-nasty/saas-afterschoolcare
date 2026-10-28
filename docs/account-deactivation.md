# Account settings and deactivation

**Status: agreed 28 October 2026, being built.**

A family can deactivate their account at a centre from Settings (in the menu). An admin reactivates it. Nothing is deleted when an account is deactivated: the centre's records about the family and their children have legal keeping periods, and are destroyed later by the retention job (`docs/child-document-retention-policy.md`), not by a countdown from deactivating.

## Account settings page

`/{location}/settings`, **Settings** in the phone menu and the desktop sidebar (after Messages; its own page, not under `/account`, so the menus don't mark Account as selected too):

- **Change password** (moved here from the Profile tab).
- **Deactivate account**, at the bottom.

## Deactivating

- **Per centre.** Logins are per location, so deactivating applies to this centre only; the family's account at another centre is untouched. Only family-only logins can deactivate: someone who also works at the centre can't.
- **No upcoming bookings.** Refused while the family has a pending or confirmed booking from today on (the database checks: `ck_family_deactivation_upcoming_bookings`). They cancel or refund those first; the page says so and links to Bookings.
- **Re-enter the password**, then a final "Deactivate your account?" confirmation.
- The database stamps when (`now()`) and a **keep-until date, stubbed as 7 years** later (`public.family_retention_period()`, one place to change). The family is never shown a figure; they're told their details stay with the centre for as long as the law requires childcare records to be kept, then they're securely destroyed.

Why 7 years: the National Regulations (reg 183) keep a child's records 3 years after their last attendance (incident, injury, trauma and illness records until the child is 25); Family Assistance Law keeps Child Care Subsidy records (attendance, fees, statements of entitlement) 7 years; tax law keeps payment records 5. 7 years is the stub until the retention work works out each record's own date. *Verify* before the first tenant goes live.

## While deactivated

The block is on the server; the website's redirect is only so the family sees an explanation.

1. **The API** (`require_permission`) checks live on every request whether this family is deactivated at this location (`public.family_is_deactivated`), and refuses with 403 "This account is deactivated." Only two family endpoints opt out (`allow_deactivated`): reading their own account and asking to reactivate. The session and logging out don't use `require_permission`, so they keep working. Live, not in the token, so it applies to logins already open.
2. **The database**: `auth.can_access_location_row` no longer gives a deactivated family their own rows at that location (children, bookings, pickups, documents, payments), so a forgotten endpoint still gets nothing and can't write. Staff access is unchanged.
3. **The website** sends every page to `/{location}/deactivated`: one button, "Ask to reactivate", which records the request (then reads "Request sent"), and Log out.

Pickup people and kiosk PINs: a deactivated family has no bookings (the precondition), so there's nothing to sign a child into.

**Bookings cancelled without a refund** (after the cutoff: CANCELLED and still PAID) don't stop a family deactivating, since they're not on the run sheet. Once deactivated:

- **Nobody can put them back**, admins included (`booking_is_reinstatable` checks `family_is_deactivated`, so the button goes and the trigger refuses).
- **An admin can still refund them.** Staff may refund any family's cancelled-but-paid booking, up to its session date (`booking_is_refundable`); families can't. When the refund goes through the booking becomes REFUNDED, keeping when it was cancelled.
- **Refunds still settle.** Stripe's webhook acts as the family; the `payments` channel (`RlsContextRepository.set_payments_channel`, set only by the webhook and payment settlement) lets RLS reach a deactivated family's rows for that.

## Reactivating

- Admin › Families › the family: "Deactivated" (and "Reactivation requested" with when), and **Reactivate** (`families u`, admins and superadmins).
- The admin home counts reactivation requests beside medical reviews and late pickups, linking to the family (later: the inbox card).
- Reactivating removes the deactivation; everything is as it was.

## Permissions

| Endpoint | Permission | Who |
|---|---|---|
| `POST /account/v1/deactivate` | `own_account u` | the family |
| `POST /account/v1/reactivation-request` | `own_account u`, allowed while deactivated | the family |
| `GET /account/v1/` | `own_account r`, allowed while deactivated | everyone |
| `GET /families/v1/reactivation-requests` | `families r` | admins, superadmins |
| `POST /families/v1/{user_id}/reactivate` | `families u` | admins, superadmins |

## Not in this build

- Destroying records when their keeping period ends (the retention job).
- An admin deactivating a family themselves.
- An audit trail of deactivations and reactivations (reactivating removes the row; the audit trail comes after the MVP).
