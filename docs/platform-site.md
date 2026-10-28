# The platform's own site

Session Pilot's own pages, on the base domain (`dev.sessionpilot.com.au`), as
opposed to a business's site (`{tenant}.{base domain}` or its own domain,
`docs/public-site.md`).

## Pages

- `/`: the landing page (`features/platform/components/PlatformLanding.svelte`):
  what the software does, for businesses running outside school hours care,
  how to get started, and Book a demo. The words are a first draft; edit
  them in that component.
- `/contact`: the platform's contact form
  (`features/platform/components/PlatformContactForm.svelte`), asking what
  it's about:
  - **Using this software for my own business** (`own_business`). Book a
    demo opens the page with this chosen (`/contact?topic=own_business`).
  - **Having software like this built** (`build_software`). The page points
    to JNB Digital (`JNB_DIGITAL_URL` in `lib/platform/site.ts`).
- The header (`PlatformHeader`) links to Contact. Log in is still a stub:
  business logins only work on a business's own site.

`/contact` is the platform's only: on a business's site it's a 404.

## The landing page's content and branding

Like a business's site (`docs/public-site.md`), the landing page's words,
photos, feature cards and the platform's branding are data, edited in place
on the page by the platform's admins (logged in to the console):

- `public.platform_site` (`schema/0004_public.sql`): one row, made by the
  seeds (`seed/0005_platform_site.sql`, the first draft): the hero's
  headline and paragraph, the about band's title and text, the logo and
  icon, the hero and about photos (with descriptions) and the three
  colours. The colours apply to every page of the platform's site.
- `public.platform_features`: the feature cards, an icon from a fixed set
  (`ck_platform_features_icon`), a title and a line, in order; at most 9.
  The first draft leans on privacy: "built to support your data
  compliance obligations", never "compliant" (there's no certification,
  and compliance is each business's own).
- Anyone reads them; only the platform's admins change them (RLS:
  `auth.is_platform_admin()`). API: `/api/platform-site/v1` on the
  platform's site only (`GET /`, `GET /files/{kind}` public; `PUT /`,
  `PUT /features`, uploads and `DELETE /files/{kind}` with the platform
  login). Files live under `branding/platform/{kind}/` in the document
  bucket, checked and re-saved as for a business.

On the page, a logged-in platform admin gets the pencil beside the hero,
the feature cards and the about band, and the photo slots. The colours,
logo (a wordmark: shown in place of the name) and site icon are set in the
console, Platform › Site. Every page of the platform's site loads the
platform's branding and whether its admin is logged in
(`routes/+layout.ts`): the colours are set on the document, the header
shows the logo, and a logged-in admin gets a Platform link beside Contact.

The logo and icon aren't seeded: they're uploaded in Platform › Site
(`docs/reference-imgs/sessionpilot-logo.png` and `sessionpilot-icon.png`).

A platform admin never has a business's data (tested in
`tests/test_platform.py`): their login is their own (`auth.platform_admins`,
its own cookie, the platform's site only), and RLS gives them only the list
of businesses with whether each takes payments and its domains, invites,
platform enquiries, this page, and switching a business off or on.

## From a business's site

The only mention of the platform on a business's site is a small
"Interested in this software?" link under the centre page's contact form,
to the platform's `/contact?topic=own_business` (`platformUrl` in
`lib/platform/site.ts`). Everything else there stays the business's own.

## Enquiries

An enquiry (`public.platform_enquiries`, `schema/0004_public.sql`) is sent
without logging in (`POST /api/platform-enquiries/v1/`, platform site only,
rate limited per address). A hidden field catches bots: they're told it
worked and nothing is kept.

Each one is:

- **kept** for the platform console, Platform â€º Enquiries (open and closed;
  close one once it's dealt with, reopen it if needed). Only the platform's
  admins read them (RLS: `auth.is_platform_admin()`).
- **emailed in full** to `PLATFORM_CONTACT_EMAIL`, from Session Pilot, with
  Reply-To the person, so it's answered from that mailbox like any email.
  With no address set, nothing is emailed.

This notice isn't one of the tenant emails in `docs/email-policy.md`: it
goes only to the platform's own mailbox and holds only what the person
typed in. It's sent as a finished `OutgoingEmail` through the outbox (no
catalogue entry or email log row).

There's no CRM: replies, notes and follow-ups live in the mailbox.
