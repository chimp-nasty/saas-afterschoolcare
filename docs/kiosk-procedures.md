# Kiosk and attendance procedures

**Status:** Draft v0.1 (20 October 2026). How centres sign children in and out with the kiosks, what staff do when something doesn't fit, and the paper fallback when a kiosk isn't working. Check against the centre's own policies (delivery and collection of children, regs 99 and 158, *verify*) before relying on it.

**Related:** the system design is in `docs/staff-platform.md` and the kiosk notes in slice 4; what goes in kiosk PIN emails is in `docs/email-policy.md`, section 4.

---

## 1. The two kiosks

Each centre has at most **one family kiosk** and **one staff kiosk**: tablets paired by an admin in Admin › Kiosks.

| | Family kiosk | Staff kiosk |
|---|---|---|
| Where | At the entrance | Where staff can reach it while supervising |
| Who | Parents and the people on a family's pickup list | Staff (staff, admins) |
| Log in with | Mobile number + 4-digit PIN | Their name + their own 4-digit staff PIN |
| Used for | Signing their own children in and out | Correcting attendance, checking ID, approving pickup people, starting and ending shifts |

Attendance is **only** recorded at a kiosk. The website shows the day's roll to staff, but nothing on it changes attendance. Every sign-in and sign-out records **who** did it, **when**, and **which kiosk**.

A person's kiosk session ends after 60 seconds without a tap, and 10 seconds after they sign a child in or out (any tap resets it). Nobody is logged in at the staff kiosk: each task (a child, or your shift) starts with your name and staff PIN, and the PIN is forgotten when the task is done, cancelled, or after 60 seconds without a tap. A one-off release asks for the PIN again (docs/portals.md).

## 2. Everyday sign in and out

**Before school care and vacation or weekend care (arriving):** the parent or pickup person signs the child in at the family kiosk on arrival.

**After school care (arriving):** children come from school without a parent. **Staff sign them in at the staff kiosk** as they arrive (or at the roll check), so the record shows who was present and when.

**Collecting (any service):** the person collecting signs the child out at the family kiosk. They can only do this if:

- they're on the family's pickup list, and
- **staff have approved them** (section 4), and
- the child was signed in. If not, the kiosk sends them to a staff member (section 5.3).

Either a pickup person or a staff member may sign a child in or out; there's no rule about which service uses which. The point is that every arrival and departure is recorded once, accurately.

**Kiosk times.** When the centre turns it on (Admin › Kiosks, "Only allow sign in and out from 2 hours before each session to 2 hours after it"), children can be signed in and out only from 2 hours before each session to 2 hours after it, at **both** kiosks. Outside that, the family kiosk tells families to see a staff member, and staff deal with it in person. Staff correcting an earlier day enter when it actually happened, which must be inside that day's times.

**Several children at once (staff kiosk).** After school care: **Sign in arrivals** signs in the session's children who've arrived from school (untick anyone absent). Before school care: **Send to school** signs out the session's children who are here, recorded as sent to school rather than collected by a person. One child can also be sent to school from their own panel. Each is all or nothing: if one child can't be done, none are, and the kiosk names the child.

**Brothers and sisters (staff kiosk).** Signing a child out lists their brothers and sisters who are here, ticked. Untick anyone staying; the rest go with the same person in one go (all or nothing). It works for approved pickup people, Collected without ID, and one-off releases.

**Printed run sheet.** Each service tab on the staff kiosk has **Print run sheet** (needs your PIN: it has families' phone numbers), and so does the admin run sheet on the website. Each session prints as whole pages of 22 rows: children alphabetically with their approved pickup people (✓ ID sighted, ⚠ not), the family phone and times already recorded, then blank numbered rows to the bottom of the last page (a second page only when the children don't fit on one), for marking off by pen at the collection point or when a kiosk is down.

**Bookings and refunds (staff kiosk).** A child's panel has a **Bookings** tab: the family's bookings from today to 2 weeks ahead, and anything still awaiting payment (read-only). Refunds are on the **Admin** tab, for admins on shift only: find the family by a child's name, choose the booking (one child, one day, refunded in full, up to and including its day), confirm, and enter your PIN again. The family is emailed once Stripe confirms the refund.

**Medical details and the action plan folder (staff kiosk).** A child's panel has a **Medical** tab: allergies, conditions, medication and their documents, marked **Approved by admin** or **⚠ Not yet reviewed by admin** while a change waits for review. The **Medical** tab of the kiosk lists every child's action plan for the physical folder (behind your PIN). Plans marked **NEW** (not yet reviewed, or uploaded in the last 7 days) need their printed copy replaced: **View** opens the plan in a new tab, where it can be printed. Close that tab when you're done, then tick **Printed**, which records your name and the time (untick it to correct a mistake). A newly uploaded plan starts unticked.

## 3. Staff PINs and shifts

- Each staff member sets their own 4-digit staff PIN on the website (My account), after re-entering their password. It's never set or changed at the kiosk.
- **Never share a staff PIN, and never use someone else's.** The PIN is how the record shows which staff member did something.
- Five wrong PINs lock it; set a new one on the website to unlock it.
- **Clock in** when you arrive and **clock out** when you leave, on the staff kiosk's Shifts tab (choose your name, then your PIN). **Only people on shift can do anything else at the staff kiosk**, admins included: the kiosk only offers their names, and the system refuses anyone else.
- If you forget to clock out, that shift stops counting at midnight. Next time you clock in, the kiosk asks what time you left, and closes the old shift with it.

## 4. A new pickup person's first pickup

When a family adds someone to their pickup list (or adds their first child, for the account holder):

1. **The person is emailed a setup PIN.** It has to be changed the first time they use the kiosk, and it stops working if it isn't used within 30 days. "Forgot PIN" at the kiosk emails a new one.
2. **On their first visit,** they log in at the family kiosk and choose their own PIN. They can sign children **in** straight away.
3. **Before they can collect a child for the first time, a staff member must approve them.** The kiosk tells them to find a staff member. Staff, at the staff kiosk:
   - find the family (from the child on the roll) and the person on the family's pickup list
   - **check photo ID** (driver's licence, passport, or proof-of-age card) and that the name matches the list, then choose **Photo ID checked**. This also approves them.
   - or, if the person is already well known to the centre (e.g. a parent staff have dealt with for years), choose **Collected without ID**, which approves them without ID and signs the child out. Use this sparingly; when unsure, ask for ID.
   - Until their ID is sighted, the person shows **⚠ ID not sighted** on the pickup list, every sign-out to them asks staff to confirm it first, and the sign-out is recorded as "ID not sighted" on the run sheet. Choose **Photo ID checked** whenever you can.
4. The person then signs the child out at the family kiosk as normal. Approval lasts until their name or phone number changes, which sends them back for a new check.

**If someone not on the list arrives to collect a child, don't release the child.** See section 5.4.

## 5. When staff sign in or out manually

All of these are done at the **staff kiosk**, each starting with your name and your own staff PIN.

### 5.1 A missed sign-in or sign-out
A parent forgot to sign in at drop-off, or left without signing out:

- **Sign the child in or out yourself.** If it happened earlier, enter the actual time; it can't be in the future.
- For a sign-out, record **who collected the child**: choose them from the family's pickup list.
- Missed records from an earlier day can be fixed the same way (choose the date on the roll).

### 5.2 After school arrivals
Sign each child in as they arrive from school, or when the roll is checked. If a booked child hasn't arrived by the expected time, follow the centre's missing child procedure.

### 5.3 A parent can't sign out because the child wasn't signed in
The kiosk refuses this deliberately: the record says the child isn't here.

1. **Confirm the child is physically present.**
2. Sign them in at the time they actually arrived (best estimate, e.g. school pickup time), then sign them out to the person collecting.
3. If the child isn't here, **don't sign anything**. Follow the missing child procedure.

### 5.4 Someone who isn't on the pickup list (a one-off release)
1. **Don't release the child yet.**
2. **Phone the account holder** on the number in their account (not a number the person gives you) and confirm they want this person to collect the child today.
3. **Check the person's photo ID** against the name the account holder gave.
4. Sign the child out at the staff kiosk as a **one-off release**: the person's full name, and a note (e.g. "Confirmed by phone with Jo Smith 5:42pm; licence checked").
5. If the account holder can't be reached, or anything doesn't match, **don't release the child.** Contact the centre's nominated supervisor.

A one-off release doesn't add the person to the family's list. If they'll collect again, the family should add them in the app.

### 5.5 Mistakes
Use **Undo** at the staff kiosk to clear a wrong sign-out, or a sign-in that hasn't been signed out, then record it correctly. Undo is recorded against the staff member.

### 5.6 Late pickups
The roll flags children still signed in after the session's end time. Follow the centre's late pickup procedure (calling the family, then emergency contacts). Late fees are worked out from the times recorded, so record the actual departure time.

## 6. Kiosk PINs for families

- **Forgot PIN:** "Forgot PIN" at the family kiosk emails a new setup PIN to the address on the pickup list (at most every 20 minutes). Staff never see or reset family PINs.
- **Locked after 5 wrong PINs:** "Forgot PIN" unlocks it.
- **No email access, or an urgent pickup:** a staff member signs the child out at the staff kiosk, choosing the person from the pickup list after the usual checks (section 4, step 3, if they aren't approved yet).
- **Wrong email address on the list:** the family corrects it in the app. A new PIN is then emailed to the new address and the old one stops working.

## 7. If a kiosk isn't working

Use paper until it's fixed. **Children are still only released to approved people**; paper doesn't relax any check.

### 7.1 Start the paper record
Keep a printed **sign-in/sign-out sheet** with each kiosk (a blank one is below). When a kiosk is down, put the sheet and a pen where the kiosk was, and tell staff on shift.

| Date | Session | Child's full name | Time in | Signed in by (name + signature) | Time out | Collected by (name) | Signature | Staff initials | Notes (ID checked, one-off release, late) |
|---|---|---|---|---|---|---|---|---|---|
| | | | | | | | | | |

- **Family kiosk down:** parents write their child's arrival or departure on the sheet and sign it. **A staff member checks every collection** against the pickup list before the child leaves (photo ID for anyone they don't know), and initials the line.
- **Staff kiosk down:** staff record their own corrections, ID checks and one-off releases on the sheet, with their initials, and note shift start and end times.
- **Both down, or no internet:** use the sheet for everything. Staff keep a head count and the printed roll (section 7.3) to the hand.

### 7.2 Once the kiosk is back
A staff member enters the paper records at the **staff kiosk**, using the **actual times** from the sheet:

- each sign-in and sign-out (sign-outs to the person on the sheet, or as a one-off release with the sheet's note)
- each ID check or approval made on paper

Then they write "Entered [date, time, initials]" on the sheet. **Keep the sheet** with the centre's attendance records for the same period as the electronic ones (see `docs/child-document-retention-policy.md`, section 5: at least 3 years).

### 7.3 Be ready before it happens
- Keep a stack of blank sheets with each kiosk.
- At the start of each session, open the day's roll on the website (Staff › Today) on a staff device, or print it, so staff know who's booked and who's on each family's pickup list even without the kiosk.

### 7.4 Common problems
| Problem | What to do |
|---|---|
| The kiosk says it isn't set up (asks for a setup code) | Its pairing was lost (e.g. browser data cleared). An admin gives it a new setup code in Admin › Kiosks. Use paper meanwhile. |
| A tablet is lost or stolen | **An admin revokes it straight away** in Admin › Kiosks; it stops working immediately. Pair a replacement with a new code. |
| No internet at the centre | Paper (section 7.1) until it's back; then enter the records (7.2). |
| One person can't log in (locked, expired PIN) | Not a kiosk fault: Forgot PIN, or staff sign them in or out at the staff kiosk (section 6). |
| The staff kiosk is down but you need to approve someone | Check photo ID and record it on the paper sheet; enter the approval at the staff kiosk when it's back. Until then, staff record that child's collection on paper. |

## 8. Review

Reviewed with the centre's delivery and collection policy, at least once a year, and after any incident involving a child's release.
