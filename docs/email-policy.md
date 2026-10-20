# Email privacy and content policy

**Status:** Agreed v1.0 (20 October 2026). Not legal advice. Review with the privacy lawyer alongside `child-document-retention-policy.md`.

**Applies to:** every email the platform sends on behalf of a tenant: what goes in it, how it's sent through Amazon SES, and what we keep about it.

---

## 1. Principle

**Email is an untrusted channel.** An email says *something happened, log in to see it*. The details stay in the app, behind a login.

Why:

- **Wrong recipients are the main risk.** Sending personal information to the wrong recipient by email was 42% of the human-error data breaches reported to the OAIC in July–December 2024 ([OAIC NDB report](https://www.oaic.gov.au/privacy/notifiable-data-breaches/notifiable-data-breaches-publications/notifiable-date-breaches-report-july-to-december-2024)). For an automated system that means a mistyped or stale address, a shared family mailbox, or a separated parent who can still read an old inbox. Minimal content keeps these from becoming notifiable breaches.
- **APP 11 asks for reasonable steps**, and the OAIC asks organisations to consider extra controls when emailing sensitive information ([OAIC](https://www.oaic.gov.au/updates/news-and-media/email-highlighted-as-a-key-risk-for-data-breaches)). Children's health information is sensitive information.
- **Subjects and addresses persist outside our control:** in SES event data, Virtual Deliverability Manager (30 days, if enabled), lock-screen previews, and the recipient's mail provider.

Emailing a family about their own account isn't an APP 8 overseas disclosure, even when their mailbox is hosted overseas. An "overseas recipient" is someone other than the individual ([APP guidelines 8.5](https://www.oaic.gov.au/privacy/australian-privacy-principles/australian-privacy-principles-guidelines/chapter-8-app-8-cross-border-disclosure-of-personal-information)). Emails about a child go to the child's parent or carer as part of the service (APP 6, primary purpose).

## 2. Content rules

| Tier | Includes | In an email |
|---|---|---|
| **Never** | Health, medical, allergy or medication details; action plans and other documents; dates of birth; children's surnames; pickup people's details; passwords; staff's free-text messages; payment card details | Never |
| **Minimal** | The recipient's first name, a child's **first name** (body only), centre name, booking or refund reference, amount | In the body only |
| **Fine** | Generic status, a link into the app, the centre's contact details | Yes |

Rules for every email:

1. **Subjects are generic.** No names, no health words, no secrets. They show on lock screens and are stored in SES event data.
2. **Words like "medical", "allergy" and "anaphylaxis" never appear** in a subject or body. "Action needed in your account" is enough.
3. **Staff's free-text messages stay in the app.** They often name a condition ("please upload the asthma plan"). The email only says there's something to look at.
4. **Links open the app and need a login.** The only exception is the password reset link, which carries a single-use token.
5. **The only secrets ever emailed** are the password reset link and the kiosk setup PIN (section 4), each with its own controls.
6. **No marketing, promotions or upsells** in service emails. Under the Spam Act they would turn a service email into a commercial message.
7. **Sent as the centre:** the From name is the centre's, and replies go to the centre's contact email.

## 3. The emails

| Email | Subject | Body | Never included |
|---|---|---|---|
| Password reset | Reset your password | Single-use link, valid 30 minutes; "if this wasn't you, ignore this email" | Whether other accounts exist, any account details |
| Password changed | Your password was changed | When; "if this wasn't you, contact {centre}" | — |
| Welcome | Welcome to {centre} | Recipient's first name; next steps (add children, pickup people); link | — |
| Booking confirmation | Your booking is confirmed | "Your booking at {centre} is confirmed. Reference {ref}, total {amount}." Link to the booking | Children, dates, sessions |
| Refund confirmation | Your refund has been processed | Amount, reference; link to the receipt | Children, dates |
| Documents requested | Action needed in your account | "{centre} has asked for documents for {child first name}. Log in to see what's needed." | The staff message, any condition |
| Child approved | Your child's profile has been approved | "{child first name} can now be booked." | Any medical detail |
| Kiosk PIN | Your kiosk PIN | "Your kiosk PIN for {centre} is {PIN}. You'll choose your own the first time you use the kiosk." | Children, phone number, centre address |

New emails are added to this table, with each item checked against section 2, before they're built.

## 4. Secrets by email

### Password reset link

- A random token of at least 256 bits, stored only as a hash.
- Single use, and it expires after 30 minutes.
- The response is the same whether or not the account exists. Requests are rate-limited.
- A successful reset is followed by the "password changed" email.
- Sent with encryption required (section 5).

### Kiosk setup PIN (a deliberate decision)

NIST SP 800-63B says email must not be used to deliver authenticators. It allows emailed recovery codes that expire within 24 hours ([NIST SP 800-63B](https://pages.nist.gov/800-63-4/sp800-63b.html)). **We email kiosk PINs anyway.** It keeps the centre's processes simple (staff never handle PINs), and these controls make the risk acceptable:

1. **A PIN alone can't release a child.** The kiosk only lets a person sign a child out once staff have approved them, after an ID check or because staff know them.
2. **The person must be present at the centre** and also know their registered phone number.
3. **The emailed PIN is a one-time setup PIN.** It must be changed at the first kiosk login.
4. **An unused setup PIN expires after 30 days.** "Forgot PIN" at the kiosk emails a new one.
5. **Five wrong attempts lock the person** (not the device) until they reset.
6. **"Forgot PIN" is rate-limited** to about 3 per hour per person, and always replies "if that number is registered…", so it doesn't reveal who's registered.
7. **The email is sent with encryption required**, has a generic subject, and contains no children, phone number or centre address.
8. **Only the PIN's hash is stored.** It's generated in the database and never logged outside development.

## 5. Sending through Amazon SES

| Control | Setting | Why |
|---|---|---|
| Account and region | One AWS account, SES in `ap-southeast-2` (Sydney) | Australian processing; AWS keeps content in the chosen region ([AWS](https://aws.amazon.com/compliance/data-privacy-faq/)) and is our processor under its data processing terms |
| Assurance | SES is IRAP-assessed at PROTECTED ([AWS IRAP](https://aws.amazon.com/compliance/services-in-scope/IRAP/)) and encrypted at rest | Supports APP 11 and customer due diligence |
| Tenants | One SES tenant per platform tenant | Each business has its own reputation and suppression list; one can be paused without affecting the others; usage per tenant |
| Sender | Our verified domain (DKIM, SPF, DMARC); From name = centre; Reply-To = centre's contact email. Tenant domains later, with tenant configuration. | Deliverability; replies reach the centre |
| Encryption in transit | **TLS required** for the password reset and kiosk PIN emails (SES drops the email rather than send it unencrypted). Other emails use TLS whenever the receiving server supports it. | Secrets never travel unencrypted; the other emails contain minimal information |
| Tracking | **No open or click tracking.** The configuration set publishes only bounce, complaint and delivery events. | Open tracking adds a hidden image that records the reader's IP address; click tracking routes every link (including the reset token) through AWS |
| Suppression | SES account-level suppression list, plus our own record of bounces and complaints | Protects shared reputation; stops sending to dead addresses |
| Templates | Templates and default wording in our code; tenants may edit the wording of fixed email types, within these rules | Locked parts (links, PIN block, footer) can't be removed; tenant text is plain text with whitelisted placeholders |

## 6. What we keep

| Record | Contents | Kept for |
|---|---|---|
| Email log (one row per email) | Tenant, location, email type, recipient's `user_id` (or pickup person), a **masked** address (`j***@gmail.com`), status (queued, sent, failed, delivered, bounced, complained), SES message ID, times, an error **code** (provider error messages can quote the address, so they aren't stored) | 2 years, then the masked address and recipient are cleared; counts are kept |
| Raw SES events (SNS payloads) | Full addresses and subjects (SES includes them) | **Not stored.** The status is copied to the log row and the payload is discarded. |

**Never stored:** email bodies, template variables, reset tokens, PINs, full recipient addresses in the log.

Usage per tenant per month comes from the email log, for the platform owner and later for tenant admins.

## 7. Privacy policy wording (tenant collection notices)

> We send service emails (for example password resets, kiosk PINs and booking confirmations) through Amazon Simple Email Service in Sydney, Australia. Emails contain as little personal information as possible; your details stay in your account. Your own email provider may store emails outside Australia. We keep delivery records (which email, when, and whether it was delivered) for 2 years. Service emails can't be unsubscribed from, and we don't send marketing.

## 8. Uncertain points

- How long SES keeps message bodies isn't published (it scans content and can provide samples during enforcement). The content rules make this low risk.
- Whether the Children's Online Privacy Code (due for registration by 10 December 2026) will cover this app: check the final text.

## 9. Review

This policy is reviewed every year, and also when an email type is added, the email provider or region changes, the Privacy Act or Children's Online Privacy Code changes, or after any breach involving email.
