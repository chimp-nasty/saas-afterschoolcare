# Contact form enquiries

**Status: agreed and built 28 October 2026.**

Each centre's page has a contact form. What people send is kept **in the app**, not as email: the centre's admins (the site supervisor) read and reply to enquiries in Admin. There's no mailbox integration and no receiving email: no MX records, no SES receiving, nothing connected to Outlook or Gmail.

## Sending one

- **Anyone**, from the centre's page, logged in or not: name, email, phone (optional), topic (enrolment, bookings, a general question) and the message (up to 3,000 characters).
- **Spam:** a hidden field only bots fill in (accepted but not kept), and 5 sends a minute per address (`app/middleware/__init__.py`). No captcha.
- It arrives through `public.submit_enquiry` (schema/0004), the only way in, since there may be no one logged in. Only for an active centre.
- **Emails** (rows in `docs/email-policy.md`):
  - to the person: **Enquiry received**, a receipt that doesn't repeat what they wrote;
  - to the centre's **enquiries address**, if the owner has set one with the centre's details (`tenancy.locations.enquiry_notice_email`): **Enquiry notice**, who it's from (first name) and the topic, with a link to read it in the app. Never the message, email or phone.

## The admins' inbox

- `enquiries r` / `u`, admins and superadmins of that centre only (RLS: `auth.is_location_admin`). Families and staff can't see them; another business's admins can't find them.
- **Open** (new and replied) by default; also new, replied, closed and all.
- **Reply:** kept with the enquiry (with who replied) and emailed to the person as **Enquiry reply**: from the SessionPilot sender under the centre's name, Reply-To the centre's contact email. The one email that carries a staff member's own words (the exception to the email policy's rule 3): the reply box reminds staff not to include health details or children's surnames, and the person's message isn't quoted back. They can reply more than once.
- **Close** when dealt with; **reopen** puts it back as new or replied. Replying to a closed enquiry reopens it.
- What the person sent never changes; only the status does (`trg_enquiries_keep`).
- The admin home counts new enquiries (the start of the Stage 3 inbox card).

## Not in this build

- Receiving replies back into the app (the person's reply goes to the centre's contact email).
- A combined view for the owner across centres.
- Retention: enquiries are kept for now; they join the retention work (`docs/child-document-retention-policy.md`) later.
