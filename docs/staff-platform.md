# Staff platform

**Status:** agreed outline, 20 October 2026. Each slice builds its part to this plan; update this file when the plan changes.

## Roles

| Role | Sees | Notes |
|---|---|---|
| `staff` | Staff screens | Runs the day: roll, reviews, families, bookings |
| `admin` | Staff screens + Admin screens | Configures the location |
| `superadmin` | Same as admin, at the location they're logged into | Tenant tools (locations, Stripe Connect) come with tenant configuration |
| Kiosk | Kiosk screens only | A registered device, not a person (kiosk slice) |

Staff and admin accounts are created by SQL or the dev seed until the Admin › Staff screen exists. Invites need the email slice.

The frontend hides what a role can't use; the API is the real gate (permissions, RLS).

## Devices

- **Staff screens:** tablet-friendly as well as desktop. The roll, finding a child and pickup checks happen on the floor. Same mobile-first rules as customer pages: 44px targets, nothing on hover, 16px inputs.
- **Admin screens:** desktop-first; they must still work on a tablet.
- Staff and admin pages may use `Page width="wide"`.

## Entry point and URLs

Everyone logs in at `/{location}/login` and lands on `/{location}/home`, which shows the home for their role.

```
/{loc}/home          role-based home: CustomerHome, or StaffHome for staff/admin/superadmin
/{loc}/staff/...     (staff) route group: staff, admin, superadmin
/{loc}/admin/...     (admin) route group: admin, superadmin
/{loc}/kiosk/...     kiosk device (kiosk slice)
```

The prefixes keep staff and admin pages clear of customer routes (`/account/children/...`). Each route group's layout checks the role with `Authorize`.

## Navigation

Sidebar on desktop, drawer on tablet and phone. Home, then the Staff section, then the Admin section (admins), then Logout. A screen is added to the sidebar when it's built.

## Screens

### Staff

| Screen | URL | Purpose | Slice |
|---|---|---|---|
| Home | `/home` | Today's sessions with counts; "needs attention" cards (reviews waiting, ID checks, late pickups). Starts with reviews and grows each slice. | Slice 2 onwards |
| Reviews | `/staff/reviews`, `/staff/reviews/{child}` | Medical review list (Pending, Requested); detail with medical details, documents, family contact, Approve and Request documents | Slice 2 |
| Today | `/staff/today` | The roll per session: booked, signed in, signed out; staff sign in/out as a fallback; ID-check approval at pickup | Kiosk |
| Children | `/staff/children`, `/staff/children/{child}` | Search every child. Tabs: Profile & medical (read-only), Documents, Pickups, Bookings, Notes | Staff dashboard |
| Families | `/staff/families`, `/staff/families/{user}` | Search families; contact, children, pickup people, bookings, messages sent; refunds | Staff dashboard |
| Bookings | `/staff/bookings` | By day or family; cancel or refund (staff can refund until the session day) | Staff dashboard |

### Admin

| Screen | URL | Purpose | Slice |
|---|---|---|---|
| Sessions | `/admin/sessions` | Calendar of service days: open or close a day, capacity | Staff dashboard |
| Services | `/admin/services` | Prices, times, ages, late fees | Staff dashboard / tenant config |
| Staff | `/admin/staff` | Invite, deactivate and change the role of staff accounts | Tenant config (after email) |
| Kiosks | `/admin/kiosks` | Register and revoke kiosk devices | Kiosk |
| Settings | `/admin/settings` | Location details, branding, contact, policies | Tenant config |

## Shared UI

- **`DataTable`:** a table on desktop that becomes stacked cards on a phone; rows link to a detail page. Every staff list uses it.
- **Status wording:** one map per feature; staff wording can differ from family wording (e.g. `features/medical-reviews/status.ts` beside `features/children/review.ts`).
- **Search, filters and paging:** `SearchFilter` and `PaginationControls`, brought up to the conventions on first use.

## Backend still needed (by slice)

- **Kiosk:** attendance endpoints, pickup identity (ID check / approve), kiosk device auth.
- **Staff dashboard:** child search with family name, child notes, family list and detail, staff-created actions (messages to families), service day create/update, a home summary endpoint.
- **Tenant config:** staff user management and invites, location settings.
