# Portals: who does what, where

**Status:** Agreed 21 October 2026. Replaces the "Staff" screens in `docs/staff-platform.md` (which still describes the earlier plan; update it as this is built). Works with `docs/kiosk-procedures.md`.

**Principle:** *Staff manage themselves. Administrators manage the business. Operations staff deliver the service.*

Three interfaces over **one set of services and one permission system**. They differ in *how you're identified* (the channel) and *what your role may do on that channel*, never in business logic: a refund from Admin and a refund at the staff kiosk run the same refund service.

---

## 1. The three portals (plus the family kiosk)

| Portal | URL | Who | Identified by | Where |
|---|---|---|---|---|
| **Staff portal** | `/staff/...` | Every employee: staff, admins, superadmins | Their own login | Anywhere |
| **Admin portal** | `/admin/...` | Admins, superadmins | Their own login | Anywhere |
| **Operations** (staff kiosk) | `/{location}/kiosk` on the paired staff tablet | Staff, admins, superadmins on site | The paired device **+ a staff PIN for every action** | On site only |
| Family kiosk | `/{location}/kiosk` on the paired family tablet | Parents and pickup people | Device + their mobile and PIN | On site only |

### 1.1 Staff portal: personal account only
**MVP:** your account details, change your password, set or change your staff PIN, see your locations and roles.

**Never here:** customer or child information, medical records, run sheets, attendance, bookings, refunds, configuration. A staff login on the website can't read any of it: the database refuses it (section 3), not just the screens.

**Later:** rosters, leave, timesheets, your own shifts.

Admins use this same portal for their own account. **The admin portal has no personal or self-service pages.**

### 1.2 Admin portal: running the business
**MVP:** location settings; kiosk devices (add, re-pair, revoke); staff accounts, roles and locations (managing *other* staff); current and upcoming run sheets; bookings and attendance records; medical review (approve, request documents); customer accounts; administrative refunds; audit history.

**Never here:** physical attendance actions (signing in or out), recording that ID was sighted, or anything else that must happen on site. Remote access doesn't bypass the kiosk.

### 1.3 Operations (staff kiosk): delivering the service
A paired tablet that always shows **today's run sheet**. **Nobody is ever logged in.** Every action starts with "Who are you?" (tap your name) and your staff PIN; once it's done, nothing is kept.

**Without a PIN** the tablet shows only: child names, session, status (not here, here, gone, late), and a **medical alert marker** (no details).

**With a PIN, one task at a time:**
- **Attendance:** sign in, sign out (choosing an approved collector), one-off releases, undo, earlier days' corrections.
- **Pickup people:** check photo ID, approve without ID.
- **Child information:** family contact, pickup list, medical details. Approved details are shown; details still awaiting re-review are shown too, marked "Not yet reviewed by admin" (staff must know about an allergy today).
- **Action plans:** an alphabetical list of every active child with a current medical document, with View / Print and when each was last updated, to keep the centre's physical action plan folder current (reprint only what changed).
- **Collection sheet:** a printable list of today's after school care children (names, tick column, times) for collecting children from school. The only daily printout.
- **Bookings and payments:** view the child's booking and payment details; refunds if the role allows.
- **Shifts:** start and end.

**One PIN per task:** a task with several screens (e.g. Sign out: pickup list → choose collector) uses one PIN, held in the page's memory for that task only and discarded when it finishes or the panel closes. The next task asks again. **Sensitive steps ask again even within a task:** one-off releases and refunds.

Medical approval stays an admin responsibility; the kiosk shows which records need admin attention but can't approve them.

## 2. Permissions: by role *and* channel

Each permission is granted to a role **on a channel**:
- **`web`**: a normal login (staff portal, admin portal, families' app).
- **`kiosk`**: the location's paired **staff** kiosk, with a staff member's PIN for this request.

| Capability | staff (web) | staff (kiosk) | admin (web) | admin (kiosk) | customer (web) |
|---|---|---|---|---|---|
| Own account, staff PIN | ✓ | | ✓ | | |
| Run sheet (today) | | ✓ | ✓ (+ upcoming) | ✓ | |
| Attendance: sign in/out, undo, corrections | | ✓ | | ✓ | |
| One-off release (re-PIN) | | ✓ | | ✓ | |
| ID check / approve pickup people | | ✓ | | ✓ | |
| Child and pickup information | | ✓ | ✓ | ✓ | own |
| Medical details, documents, action plans | | ✓ | ✓ | ✓ | own |
| Medical review (approve, request documents) | | | ✓ | | |
| Bookings and payments (view) | | ✓ | ✓ | ✓ | own |
| Refunds (re-PIN at the kiosk) | | | ✓ | ✓ | own, within the window |
| Shifts | | ✓ | | ✓ | |
| Kiosk devices, location config, staff accounts | | | ✓ | | |

Refunds and one-off releases at the kiosk are role-controlled grants, so a tenant can change who may do them without code changes.

## 3. How it's enforced

- **One identity per request.** At the staff kiosk, each request carries the device cookie, the staff member and their PIN. The API checks the device (active, this location, staff kind) and the PIN (5 wrong locks it; reset on the website), then runs the request **as that staff member, at that location, on the `kiosk` channel**: the database session gets `app.user_id`, `app.location_id`, `app.channel = 'kiosk'` and `app.kiosk_device_id`. Every existing service and RLS policy then applies unchanged, and every change is recorded against the staff member and the device.
- **Permissions by channel:** `auth.role_permissions` records the channel of each grant; the API checks the permission for the request's channel.
- **The database enforces the split:**
  - RLS treats the **staff** role as location staff **only on the kiosk channel**. On the web, a staff login reads no child, customer, medical, booking or attendance rows, even if a route is misconfigured. Admins and superadmins keep web access.
  - Physical actions (attendance, ID checks, shifts) require the kiosk channel **and** a staff-kind device (existing triggers, checking the channel).
- **The family kiosk is unchanged:** its people aren't users, so it keeps its narrow `kiosk_*` database functions.

## 4. Build order

1. This document.
2. **Backend:** permissions by channel; channel-aware RLS helpers; staff kiosk requests run as the staff member with a per-request PIN (no kiosk staff sessions); attendance and ID triggers check the channel; tests that a staff login on the web sees no child data.
3. **Move screens:** medical reviews and the run sheet to `/admin`; the staff home becomes the account page; staff role web permissions stripped. Every login also gets its own account (`/account/v1`: read-only details, change password with the current one, then the "password changed" email); families change their password on their account page.
4. **Expand the staff kiosk:** pre-PIN view tightened, medical alerts and details, action plans, collection sheet, booking and payment info, refunds.
5. **Full scenario tests** across the three portals and the family kiosk (`backend/tests/test_scenarios.py`).

**Status:** steps 1–5 done (21 October 2026); 380 tests passing.

## 5. Decisions recorded

- Per-action PIN at the staff kiosk; no logged-in state; one PIN per task; re-PIN for one-off releases and refunds.
- Staff role: no customer, child or medical data on the web. Admin: full web administration, no physical actions remotely.
- Kiosk medical details shown when approved, and also while awaiting re-review (marked).
- No daily medical printout: an alphabetical action plan list keeps the physical folder current; the collection sheet is the only daily printout.
- Every employee's own account lives in the staff portal; the admin portal has no self-service pages.
- Same services and permissions behind every portal; the channel and role decide access.
- Only people on shift act at the staff kiosk, admins included (`public.staff_on_shift`: an open shift started on the location's today). It's checked by the API for every PIN action except clocking in or out, and by the attendance and pickup ID triggers. A forgotten clock-out is closed with the time the person gives when they next clock in.
- The staff kiosk is in tabs: Run sheet, Shifts, Medical, Admin. Before a PIN, the run sheet shows who signed each child in and out with shortened names ("Sam L.").
- Admins can refund at the kiosk with the same rules as the website: past the family's cutoff, up to and including the session day.
- Run sheet: a tab per service on the day, with empty rows up to that service's capacity and places remaining. Bulk actions: after school care signs in arrivals, before school care sends children to school (`attendance_records.sent_to_school`, before school care only); all or nothing.
- Action plan folder: staff tick **Printed** on each plan (`child_documents.printed_at`/`printed_by_user_id`, set only through `public.set_document_printed` by staff on shift at the staff kiosk; `child_document_prints u`, kiosk only).
- The admin run sheet is the staff kiosk's run sheet view (`run_sheet_board`/`run_sheet_sessions`, shared with the kiosk), read-only: no taps, no bulk actions, print per service.
- Notes and messages (slice 4-5): admins and superadmins write staff notes about a child on the family's page (`child_notes` c/r/d, web); notes are fixed once saved (`trg_child_notes_rules`), never shown to the family (RLS: location staff only), and read at the staff kiosk in the child's Notes tab (`child_notes r`, kiosk), with a Notes marker on the run sheet. Messages to the family (`actions` c/d) are read in their account; one can be withdrawn until it's read (`trg_actions_rules`), and the email only says there's a message.
- Admin and superadmin split (slice 4, by permission only): service settings are superadmins' (`location_services u`); service days are seen by admins (`service_day_overview r`) and changed by superadmins (`location_service_days c/u/d`); staff accounts are seen, added (as staff), re-invited, renamed and PIN-reset by both (`staff_accounts c/r/u`), while making or unmaking admins (`staff_admin_roles u`) and removing people (`staff_accounts d`) are superadmins'. Families (search, the family page, phone and address corrections, bookings with refunds, attendance history, payments) are both admins' and superadmins' (`families r/u`, `refunds c`), this centre only. Superadmins themselves are set up with the tenant. The database still keeps bookings and staff safe whoever acts (no booked day closed or shrunk, nobody changes their own role, always an admin).
- Kiosk bookings and refunds: a child's panel shows the family's bookings (today to 2 weeks ahead, and anything unpaid). Admins on shift refund one booking at a time on the Admin tab (re-PIN), with the website's rules: past the family's cutoff, up to and including the session day (`enforce_refund_rules` checks `is_location_admin`). Refunds at the kiosk keep the kiosk channel through every step.
- Kiosk service times: children are signed in and out, at either kiosk, only from 2 hours before to 2 hours after each session, by the time recorded (`public.service_day_signing_window`), per location, switched on and off by admins on /admin/kiosks (off in the dev seed). Anything outside is dealt with in person for the MVP.
