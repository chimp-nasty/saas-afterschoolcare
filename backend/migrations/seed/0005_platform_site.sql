-- The platform's landing page (docs/platform-site.md): its one row and its
-- first feature cards, a draft the platform's admins edit on the page.
-- The logo, icon, photos and colours are added there too.
INSERT INTO public.platform_site (id, headline, hero_text, about_title, about)
VALUES (
    TRUE,
    'Simple software for outside school hours care',
    'Bookings, payments, sign-in and family accounts in one place, on your own branded site.',
    'Less admin. More time for children.',
    'Session Pilot brings bookings, payments, attendance, medical reviews and family communication into one simple platform, so your team spends less time on paperwork and more time with the children in their care.'
);

INSERT INTO public.platform_features (position, icon, title, description)
VALUES
    (0, 'location', 'Your data stays in Australia', 'Families'' details, documents and emails are stored and sent from Australian data centres.'),
    (1, 'privacy', 'Only what''s needed', 'Emails never carry health details or children''s surnames: families log in to see anything sensitive.'),
    (2, 'staff', 'Access by role', 'Staff see only their own centre, and only what their role needs.'),
    (3, 'medical', 'Medical details kept private', 'Families upload action plans; staff review them before a child can be booked.'),
    (4, 'booking', 'Online booking and payments', 'Families book sessions and pay by card, straight into your own Stripe account.'),
    (5, 'kiosk', 'Sign-in kiosk', 'Parents sign children in and out on a tablet. Staff approve who collects each child.');
