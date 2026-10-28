# Owner dashboard

**Status: agreed 28 October 2026, being built.**

The business owner's first page in Business settings (`/business`): how the business is doing, what needs attention, and who its families are. Owner only (a tenant permission, `tenant_dashboard r`), across all centres with a centre filter. The setup checklist stays below it until everything's set up.

## Period

A centre picker (All centres, or one), then **[Prev] [This week] [Next]**, stepping a week at a time as far as you like, and **[All time]** on the right; under them, "Viewing {Monday} to {Sunday}". Weeks run Monday to Sunday in each centre's own timezone. Each headline number shows the week before beside it (▲/▼ %), except All time.

## Headline numbers

| Card | Counts |
|---|---|
| **Revenue** | Paid sessions **taking place** in the period (by session date), net of refunds: the price of every booking still paid for (confirmed, or cancelled without a refund). Next week shows what's already booked for it. |
| **Bookings** | Confirmed, paid sessions taking place in the period. |
| **Active families** | Families with at least one of those. |
| **Registrations** | New family accounts at a centre in the period (by when they signed up, the centre's date). None for next week. |
| **Refunds** | Refunds that went through in the period: how many and how much. None for next week. |

## Attention required (now, not by period)

- **Medical reviews:** children waiting for a review.
- **Follow-ups:**
  - new enquiries nobody has replied to (`docs/enquiries.md`)
  - reactivation requests (`docs/account-deactivation.md`)
  - documents requested from families that haven't come back (medical reviews waiting on the family)
  - **payments needing a refund:** paid after their places were released (a hold lapsed or the booking was cancelled first), so nothing in the app is paid and it can't be refunded there. Listed with their booking reference, to refund in the Stripe dashboard (search the reference).
- **Cancelled without a refund** in the period: paid sessions the family cancelled after the cutoff, in case of a goodwill refund.

## Customer insights

- **Returning families:** active in the period and had a paid session before it (All time: more than one paid booking).
- **Inactive 30 days:** family accounts with no paid session in the last 30 days.
- **Average sessions per family:** bookings ÷ active families for the period.

## How it's built

- The numbers are worked out in the database: `public.owner_dashboard_*` functions (schema/0004), SECURITY DEFINER because the owner in Business settings has no centre session for RLS to scope by; each checks `auth.has_tenant_permission(tenant, 'tenant_dashboard', 'r')` itself and only counts that tenant's centres.
- `GET /business/v1/dashboard?week=-1&location_id=…` (weeks from this one) or `?all_time=true`: one response with the period's numbers, the previous period's, attention and insights.
- Stat cards; no charts yet.
