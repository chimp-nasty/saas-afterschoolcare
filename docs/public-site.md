# Public site: new look, centre pages and programs

**Status: agreed 27 October 2026; stages 1 and 2 built.** Build in the stages below, stopping after each for a rebuild, tests and a look in the browser.

Every business gets the same public site layout, styled from its own logo, colours, text and photos. The starting point was After 3's mockup (`docs/reference-imgs/`), adapted to the platform: its brief is After 3's (high-school students, its imagery rules) and isn't followed where it doesn't fit other businesses.

## 1. Pages

| Page | What it is | Built from |
|---|---|---|
| `/` | The business's landing page | Business content (hero, highlights, about, FAQs) and its centres |
| `/locations` | Every centre: name, address, the services it runs with times, its programs (linked), a map link, **Go to centre** | Centres and their service settings |
| `/about` | The business's about text (as today). A fuller page may come later | Business content |
| `/{location}` | The centre page: service first (see 3) | Business content plus the centre's own |
| `/{location}/programs` | One section per service the centre offers (see 4) | The centre's service settings |

`locations` and `about` join the reserved centre codes (`ck_locations_code_reserved`), so no centre can hide those pages. `programs` lives under the centre, next to its other pages (`home`, `bookings`, `account`...), and doesn't clash.

## 2. Header, menu and bottom bar

The header is fixed to the top on every page; the families' bottom bar is fixed to the bottom.

| Who, where | Desktop header | Mobile header | Below |
|---|---|---|---|
| Logged out, business pages (`/`, `/locations`, `/about`) | Logo · Locations · About · **Enrol now** · Log in | Logo + menu (the same links) | |
| Logged out, a centre's pages | Logo · Programs · Locations · About · **Enrol now** · Log in | Logo + menu | |
| Family, logged in | Logo · About · Programs · bell; the sidebar as today | Logo · bell · menu (About, Programs, Log out) | Bottom bar unchanged: Home, Bookings, Account |

- **Programs** only appears where there's a centre to show programs for; on business pages each centre's programs are reached from `/locations`.
- **Enrol now** replaces "Create an account": the centre's registration, or a new booking when logged in. On business pages it goes to `/locations` (a centre has to be chosen first).
- Logging in goes to the family's `/home`, as today. Account features stay in the bottom bar.
- Staff, admins, owners and the platform keep their current navigation. No public link leads to them.

## 3. The centre page `/{location}`

Desktop, top to bottom (mobile stacks the same content in order):

1. **Hero:** the centre's name as the eyebrow; the business's headline and paragraph; **Enrol now** and **View program**; a photo (the centre's, else the business's).
2. **Facts row:** address · the featured service ("After School Care · 3:00–6:00pm Mon–Fri") · its age label.
3. **Highlights and next session:** `| highlight | highlight | highlight | highlight | Next session |`. On mobile the next-session card comes after the highlights.
4. **About the program:** the business's about text, a photo, and this centre's programs, each linking to its section of `/{location}/programs`.
5. **Find us:** the address and an embedded map (stage 7; until then a "View on map" link).
6. **FAQs.**
7. **Footer:** contact, privacy, terms.

Dropped from the mockup: "Today at..." (a daily activity list someone would have to keep up).

- **Featured service:** each centre picks one (defaults to its first active service).
- **Age label:** per service, free text, defaulting to "Ages X to Y" from the service's age limits; After 3 can write "Years 7 to 12".
- **Next session:** the featured service's next session that hasn't finished yet, from its active days and times; the sign-in window doesn't apply.
- A section with nothing to show is left out. Placeholder times, prices or addresses are never shown as if real.

## 4. Programs `/{location}/programs`

One section per service the centre offers, written by the centre's admin in Admin › Service settings, next to the settings already there. Per service:

- description (the existing `description`)
- what's included
- drop-off and pickup
- what to bring
- activities
- age label (see 3)
- a photo (stage 6)

Under each, from the settings: days, times and price.

Centres write their own text, even when it's the same as another centre's: copying is by hand for now.

## 5. Look and colours

- The mockup's type scale, spacing, rounded cards and button styles become the platform's public look (the font is already Inter).
- Each business sets three colours: **primary**, **secondary** and a new **accent**. The platform sets backgrounds and neutrals; there are no separate success or error colours.

## 6. Who edits what

| Who | Where | What |
|---|---|---|
| The business owner | Business settings › Site | Hero headline and paragraph, the four highlights (each from a small preset set, with editable text), the three colours, the hero and about photos, about text, FAQs (as today) |
| The centre's admin | Admin › Service settings, Admin › centre details | Programs, drop-off and pickup, age labels, the featured service, the centre's photo |

## 7. Stages

Each ends with something to look at; **DB** stages need a dev rebuild.

1. **Foundation (DB):** `accent_color` and its picker in Business settings › Site; `locations` and `about` reserved; the public look (`SiteSection` bands, `SiteHeading`, `display-text`/`headline-text`, softened secondary and accent) on `/` and the centre page, with today's content. Staff and admin screens unchanged.
2. **Header and navigation:** the fixed header and its menus for each case in section 2; the bottom bar fixed and otherwise unchanged. Links point at `/` sections until stage 3.
3. **`/locations` and `/about`** from existing data; `/` links to them.
4. **Business content (DB):** hero headline and paragraph, the four highlights (preset icons, editable text), their editor in Business settings › Site, shown on `/`.
5. **Centre page data (DB):** the featured service and age labels (Admin › Service settings), and the API's next session.
6. **The centre page** (section 3), without photos and map.
7. **Program content (DB):** the program fields and their editor in Admin › Service settings.
8. **The programs page** `/{location}/programs`, linked from the centre page, header and `/locations`.
9. **Photos (DB):** the four kinds, stored like the logo, their editors (with a note that photos of children need the family's consent), shown on the pages; every slot optional.
10. **Embedded map:** turn each centre's address into coordinates when it's saved (the `latitude`, `longitude` and `google_place_id` columns already exist), and embed Google Maps in Find us and on `/locations`. Needs a Maps key; how to restrict it with businesses on their own domains is decided then.

Out of scope: the customer-facing wording review (planned separately), a fuller `/about`, centre notices.
