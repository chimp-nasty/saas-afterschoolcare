# Public site: new look, centre pages and programs

**Status: agreed 27 October 2026; stages 1 to 9 built.** Build in the stages below, stopping after each for a rebuild, tests and a look in the browser.

Every business gets the same public site layout, styled from its own logo, colours, text and photos. The starting point was After 3's mockup (`docs/reference-imgs/`), adapted to the platform: its brief is After 3's (high-school students, its imagery rules) and isn't followed where it doesn't fit other businesses.

## 1. Pages

| Page | What it is | Built from |
|---|---|---|
| `/` | The business's landing page | Business content (hero, highlights, about, FAQs) and its centres |
| `/locations` | Every centre: name, address, the services it runs with times and ages (no prices), its programs (linked), a map link, **Go to centre** | Centres and their service settings |
| `/about` | The business's about text (as today). A fuller page may come later | Business content |
| `/{location}` | The centre page: service first (see 3) | Business content plus the centre's own |
| `/{location}/programs` | One section per service the centre offers (see 4) | The centre's service settings |

`locations` and `about` join the reserved centre codes (`ck_locations_code_reserved`), so no centre can hide those pages. `programs` lives under the centre, next to its other pages (`home`, `bookings`, `account`...), and doesn't clash.

## 2. Header, menu and bottom bar

The header is fixed to the top on every page; the families' bottom bar is fixed to the bottom.

| Who, where | Desktop header | Mobile header | Below |
|---|---|---|---|
| Business pages (`/`, `/locations`, `/about`) | Logo · Locations · About | Logo + menu (the same links) | |
| Logged out, a centre's pages | Logo · Programs · Locations · About · **Enrol now** · Log in | Logo + menu | |
| Family, logged in | Logo · About · Programs · bell; the sidebar as today | Logo · bell · menu (About, Programs, Log out) | Bottom bar unchanged: Home, Bookings, Account |
| Business settings (`/business`) | The same header: Logo · Locations · About · Business; its sidebar below | Logo + menu (its sidebar's drawer) | |

- **About, Programs and Home** (`/{location}/home`) are in the header for everyone logged in at the centre: families, staff, admins and the owner, who edits About and the programs there (user decisions, 27 October 2026). The centre's own page has no sidebar even when logged in; Home leads back to the rest.
- **Business** (`/business`) is added after the other links for the business's owner, wherever they are (user decision, 27 October 2026). Shown from the session's tenant permissions; `/business` and its API refuse anyone else themselves.

- **Programs, Log in and Enrol now** belong to a centre, so they're only on a centre's pages (user decision, 27 October 2026); on business pages each centre is reached from `/locations`.
- **Enrol now** replaces "Create an account": the centre's registration, or a new booking when logged in.
- **Prices** are only on a centre's own pages, not the business pages (`/locations` shows times and ages).
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

One section per service the centre offers, written inline on the page by a superadmin there (section 6). Per service:

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

Page text is edited **inline**, on the page itself (user decision, 27 October 2026): a pencil on each editable section, always visible to whoever may edit it, turns that section into its form in place, with Save and Cancel. Saving publishes at once (no drafts). For them, an empty section shows a prompt to add it; for everyone else it stays hidden. **Desktop only** (from `md`): on a phone the pages show as everyone sees them. The API and its permission checks are unchanged; only where the forms live moves.

| Who | Inline, on the page | Elsewhere |
|---|---|---|
| The business owner (tenant permission `tenant_settings`) | Hero headline and paragraph and the highlights (`/` and the centre pages), About (`/about`, previewed on `/`), FAQs (`/`) | Business settings › Your site: colours, logo, site icon, policies, the hero and about photos |
| A superadmin at the centre (the owner is one at every centre) | Program text (`/{location}/programs`) | Admin › Service settings: price, times, ages and age label, the featured service; the centre's photo |

## 7. Stages

Each ends with something to look at; **DB** stages need a dev rebuild.

1. **Foundation (DB):** `accent_color` and its picker in Business settings › Site; `locations` and `about` reserved; the public look (`SiteSection` bands, `SiteHeading`, `display-text`/`headline-text`, softened secondary and accent) on `/` and the centre page, with today's content. Staff and admin screens unchanged.
2. **Header and navigation:** the fixed header and its menus for each case in section 2; the bottom bar fixed and otherwise unchanged. Links point at `/` sections until stage 3.
3. **`/locations` and `/about`** from existing data; `/` links to them.
4. **Business content (DB):** hero headline (the existing `tagline`) and paragraph (`tenants.hero_text`), up to four highlights (`tenancy.tenant_highlights`: an icon from 8, a title and a line; the editor suggests wording per icon and starts with four suggestions, but nothing shows until saved), their editors in Business settings › Site, shown on `/`.
5. **Centre page data (DB):** `age_label` and `is_featured` on each service's config (one featured per location; Admin › Service settings, superadmins, like the rest of those settings), and `GET /location-services/v1/public/{location}/featured`: the featured (else first offered) service, its next session and its weekdays over four weeks, from `public.service_upcoming_sessions` (service days aren't public, so only those facts leave the database).
5b. **Inline editing of business content:** the header's Business link, then `EditableSection` (a pencil, the section's form in place, Save and Cancel) for the hero, highlights, About and FAQs on `/` and `/about`; those editors left Business settings › Your site (now colours, logo, icon, policies) and About left Business details. `PUT /business/v1/site` now changes only the fields sent (so the hero's words and the colours are saved apart) and carries `about`.
6. **The centre page** (section 3), without photos and map; its hero, highlights, about and FAQs editable inline like `/` (the owner counts as the owner anywhere on the site, logged in at any centre or Business settings). Until stage 8, "View program" and the program links go to its services band (with prices). The main button is Enrol now, Book a session for a family logged in here.
7. **Program content (DB):** `inclusions`, `drop_off_pickup`, `what_to_bring` and `activities` (each optional, up to 2000 characters) on each service's config, after its `description`; saved through the existing `PATCH /location-services/v1/{id}/config` (superadmins; only the fields sent; blank clears).
8. **The programs page** `/{location}/programs` (built with 7): each offered service in full, edited inline by a superadmin logged in at the centre; each program has its own anchor (its id). Linked from the header's Programs, the centre page's View program and its list of programs, and each service on `/locations`. Like the centre page, no sidebar.
9. **Photos (DB), edited inline** (user decision, 27 October 2026), each with an optional description for screen readers. Stored in the documents bucket like the logo, but **re-saved** as a JPEG at most 2400px on its longest side, which drops all metadata (a phone photo's EXIF can hold where it was taken); uploads up to 8 MB, PNG, JPEG or WebP. Each editor notes that photos of children need their families' agreement. Every slot optional.
   - **9a:** the business's hero photo (beside the headline on `/`; the centre page uses it until 9b) and about photo (`/`, `/about`, the centre page), edited inline by the owner (`EditablePhoto`). Links carry the photo's version (`?v=`) so a replaced photo isn't hidden by a cached redirect.
   - **9b:** a centre's photo (`tenancy.locations.photo_key`/`photo_alt`: its page's hero, else the business's; its card on `/locations`), set by the **owner** from anywhere, like the centre's other details (`/business/v1/locations/{id}/photo…`, `tenant_locations` u); and each program's photo (`location_service_config.photo_key`/`photo_alt`: beside the program on its page), set by a superadmin logged in at the centre like the program's text (`/location-services/v1/{id}/photo…`; its description through the config's `photo_alt`). Both go through `PhotoUploads` (`app/integrations/storage/photo_uploads.py`), under `branding/locations/{location}/…`.
10. **Embedded map:** turn each centre's address into coordinates when it's saved (the `latitude`, `longitude` and `google_place_id` columns already exist), and embed Google Maps in Find us and on `/locations`. Needs a Maps key; how to restrict it with businesses on their own domains is decided then.

Out of scope: the customer-facing wording review (planned separately), a fuller `/about`, centre notices.
