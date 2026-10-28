// The feature cards on the platform's landing page (docs/platform-site.md):
// the icons a card can have (ck_platform_features_icon), each with a name
// for the editor's picker and the wording a new card starts with.
import {
	BadgeCheck,
	CalendarCheck,
	ChartColumn,
	CreditCard,
	FileText,
	HeartPulse,
	House,
	LockKeyhole,
	Mail,
	MapPin,
	ShieldCheck,
	TabletSmartphone
} from 'lucide-svelte';

import type { PlatformFeatureItem } from '$lib/api/schema';

export type PlatformFeatureIcon = PlatformFeatureItem['icon'];

export const PLATFORM_FEATURE_ICONS: Record<
	PlatformFeatureIcon,
	{ icon: typeof ShieldCheck; name: string; title: string; text: string }
> = {
	location: { icon: MapPin, name: 'Australia', title: 'Your data stays in Australia', text: 'Stored and sent from Australian data centres.' },
	privacy: { icon: ShieldCheck, name: 'Privacy', title: "Only what's needed", text: 'Emails never carry health details.' },
	lock: { icon: LockKeyhole, name: 'Security', title: 'Secure by design', text: 'Every record is locked to its own business and centre.' },
	staff: { icon: BadgeCheck, name: 'Staff', title: 'Access by role', text: 'Staff see only what their role needs.' },
	family: { icon: House, name: 'Families', title: 'Family accounts', text: 'Families keep their own details up to date.' },
	medical: { icon: HeartPulse, name: 'Medical', title: 'Medical reviews', text: 'Staff review action plans before a child is booked.' },
	booking: { icon: CalendarCheck, name: 'Bookings', title: 'Online bookings', text: 'Families book sessions online.' },
	payment: { icon: CreditCard, name: 'Payments', title: 'Card payments', text: 'Paid straight into your own Stripe account.' },
	kiosk: { icon: TabletSmartphone, name: 'Kiosk', title: 'Sign-in kiosk', text: 'Children signed in and out on a tablet.' },
	email: { icon: Mail, name: 'Email', title: 'Automatic emails', text: 'Confirmations and reminders sent for you.' },
	dashboard: { icon: ChartColumn, name: 'Dashboard', title: 'Owner dashboard', text: 'Revenue and bookings across every centre.' },
	document: { icon: FileText, name: 'Documents', title: 'Documents in one place', text: 'Policies and medical documents kept together.' }
};

export const PLATFORM_FEATURE_ICON_NAMES = Object.keys(PLATFORM_FEATURE_ICONS) as PlatformFeatureIcon[];

export function presetFeature(icon: PlatformFeatureIcon): PlatformFeatureItem {
	const preset = PLATFORM_FEATURE_ICONS[icon];

	return { icon, title: preset.title, text: preset.text };
}
