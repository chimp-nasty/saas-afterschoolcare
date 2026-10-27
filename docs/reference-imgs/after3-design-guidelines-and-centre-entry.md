# After 3 — Visual Guidelines and Centre Entry Page

Status: Design direction / implementation brief, not a final specification.

## 1. Product distinction

After 3 supports **high-school students**. Avoid primary-school childcare cues: toddler photographs, suns, doodles, nursery colours, oversized playful icons, and language that infantilises students.

Two page types share one design system:

- `/` — **Marketing landing page**: explain After 3, build confidence, show programs and locations, encourage enquiries.
- `/{locationSlug}` — **Centre service entry point**: identify the centre, make session booking and family access obvious, communicate operational details.

Do not create two independent design systems or code branches. Use shared components and responsive variants, with different page compositions.

## 2. Shared visual language (based on Design 3: Contemporary and Structured)

### Layout
- Clean, contemporary, restrained, accessible and friendly to teenagers and parents.
- Generous whitespace, strong alignment, clear content hierarchy.
- Constrained content width on desktop (approximately 1120–1200px); consistent horizontal gutters.
- Grid-based desktop sections; mobile layouts deliberately reflow into stacked content.
- Rounded but restrained cards and image corners (approximately 12–20px).
- Use section backgrounds sparingly to separate related information; avoid excessive cards or decorative flourishes.

### Typography
- Modern sans-serif with a strong, readable heading hierarchy.
- Short, direct headings; avoid childish slogans and corporate jargon.
- Body copy concise and legible; never shrink important information to fit an aesthetic.
- Use labels/eyebrows for context, e.g. `YOUR CENTRE`, `SESSION DETAILS`, `BEFORE YOU ARRIVE`.

### Imagery
- Authentic-looking **secondary/high-school-age students**, not toddlers or primary-school children.
- Prefer realistic photos of teens socialising, playing sport, creating, or spending time in supervised settings.
- Photos should support content rather than displace important actions.
- For production, use appropriately licensed imagery or real centre photos with suitable consent.
- AI-generated concept imagery is for design exploration only.

### Colour and iconography
- **Colour scheme intentionally undecided.** Mockups may use neutrals and a temporary accent, but do not lock in a palette.
- Clear contrast and a single primary action style; outlined secondary actions.
- Simple consistent line icons for logistics and program information; no childish stickers or sunbursts.

### Components
- Shared: brand/header, buttons, typography, content container, section headings, information cards, photography treatment, FAQ accordion styling, footer.
- Centre-specific: location identity, booking CTA, session information, location details, family account access, operational notices.
- Design for accessibility: keyboard operation, visible focus states, semantic landmarks, readable text, sufficient contrast, touch targets.

## 3. Centre page intent

Route: `https://<after3domain>/<locationSlug>` (example: `/location1`).

The centre page is **service-first**. A parent arriving via a school link or saved bookmark should be able to answer quickly:
1. Am I at the right centre?
2. How do I book a session?
3. How do I access or manage my family's bookings?
4. When and where does the service operate?
5. What should I know before attending?

The centre name must be prominent; avoid a giant generic marketing hero.

## 4. Suggested desktop page structure

```text
┌──────────────────────────────────────────────────────────────────────┐
│ After 3                 Our Program   Locations        Family Login  │
├──────────────────────────────────────────────────────────────────────┤
│ YOUR CENTRE                                                          │
│ [Centre Name]                                [Teen activity photo]    │
│ After-school sessions for high-school students                       │
│ [Book a Session]  [View Session Details]                              │
│                                                                      │
│ [Session hours]       [Location]         [Session price, if set]      │
├──────────────────────────────────────────────────────────────────────┤
│ QUICK ACTIONS                                                        │
│ [Book a session]      [Manage bookings / Family login]               │
├──────────────────────────────────────────────────────────────────────┤
│ SESSION DETAILS                 │  BEFORE YOU ARRIVE                  │
│ Days and hours                  │  Arrival and collection             │
│ What students can expect        │  What to bring                      │
│ Eligibility / requirements      │  Key centre-specific information    │
├──────────────────────────────────────────────────────────────────────┤
│ FIND US                                                              │
│ Address, arrival instructions, optional map, contact                 │
├──────────────────────────────────────────────────────────────────────┤
│ Common questions / centre notices                                    │
├──────────────────────────────────────────────────────────────────────┤
│ Footer: contact, privacy, terms, refunds, main After 3 site          │
└──────────────────────────────────────────────────────────────────────┘
```

## 5. Suggested mobile page structure

```text
┌────────────────────────────┐
│ After 3             [Menu] │
├────────────────────────────┤
│ YOUR CENTRE                │
│ [Centre Name]              │
│ After-school sessions      │
│ [Book a Session]           │
│ [Family Login]             │
│ [Compact centre image]     │
├────────────────────────────┤
│ Hours  •  Location         │
├────────────────────────────┤
│ Session Details            │
│ Days, hours, information   │
├────────────────────────────┤
│ Before You Arrive          │
│ Collection / requirements  │
├────────────────────────────┤
│ Find Us                    │
│ Address / directions       │
├────────────────────────────┤
│ FAQs / Contact / Footer    │
└────────────────────────────┘
```

Mobile priority: centre identity, booking, login, and essential session logistics **before** decorative content. Avoid repeating too many large CTA cards or using a sticky booking button unless testing demonstrates it is helpful.

## 6. Behaviour and routing assumptions to validate

- `/{locationSlug}` is the public entry point for a specific centre.
- **Book a Session** should enter the existing location-scoped customer booking flow; don't invent an unauthenticated checkout route.
- **Family Login** should lead to the existing location-aware authentication flow and return the family to that centre.
- Authenticated families may see a context-aware action such as **Manage Bookings** in place of **Family Login**.
- Centre-specific information (name, address, hours, available session days, price, notices, contact details) should come from existing tenant/location configuration or an appropriate content model, not hard-coded per-centre pages.
- Never display placeholder prices, times, or addresses as if they are confirmed.
- No public navigation to tenant owner controls, platform superadmin, staff portal, or kiosk operations. Those remain separate access paths.
- Preserve tenant isolation and location scope; the public slug is not an authorisation boundary.

## 7. Content and UX priorities

### Above the fold
- Brand + centre name
- One-sentence service description
- Primary CTA: **Book a Session**
- Secondary CTA: **Family Login** or **Manage Bookings**
- At least one useful operational fact, e.g. session hours if configured

### Below the fold
- Session days and times
- What happens at the centre (brief, not a marketing essay)
- Arrival and collection instructions
- Address and contact details
- Important notices and FAQs
- Policy links in footer

Avoid turning the centre page into a duplicate of the marketing homepage. Users can follow **Our Program** to learn more, but booking and logistics remain the main purpose.

## 8. Responsive design approach

Implement **one responsive page**, not a separate mobile branch:
- Desktop: compact split hero, two-column information blocks, horizontal action areas.
- Mobile: stacked hero, full-width primary CTA, concise information panels, accessible menu.
- Reuse content and components; alter layout with CSS breakpoints and fluid sizing.
- Validate at common mobile widths and tablet, not just desktop.

## 9. Open design decisions

- Final brand colours and fonts.
- Whether centre photo is required or optional.
- Whether authenticated families land on this public page or are directed to their booking dashboard.
- Which centre details are configurable and who may edit them.
- Whether public centre notices are needed for the MVP.
- Exact booking and login destinations, determined by the existing application routing.

## 10. Suggested implementation order

1. Agree on the centre desktop/mobile visual direction.
2. Inventory current booking, authentication, and location configuration routes.
3. Define a typed location page content contract and sensible missing-data behaviour.
4. Build the responsive public centre entry page using shared design tokens/components.
5. Wire real CTAs into existing customer flows.
6. Test small-screen UX, keyboard access, centre switching, and tenant/location scoping.
