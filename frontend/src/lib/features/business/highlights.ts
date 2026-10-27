// The highlights under the public site's hero (docs/public-site.md): the
// icons a business can choose (ck_tenant_highlights_icon) and the wording
// the editor suggests for each, which the owner may change.
import {
	Apple,
	BadgeCheck,
	BookOpen,
	CalendarCheck,
	MapPin,
	ShieldCheck,
	Users,
	Volleyball
} from 'lucide-svelte';

import type { HighlightItem } from '$lib/api/schema';

export type HighlightIcon = HighlightItem['icon'];

export const HIGHLIGHT_PRESETS: Record<HighlightIcon, { icon: typeof ShieldCheck; title: string; text: string }> = {
	shield: { icon: ShieldCheck, title: 'Safe and supervised', text: 'Qualified staff and a safe environment.' },
	community: { icon: Users, title: 'A welcoming community', text: 'Somewhere to make friends and belong.' },
	activities: { icon: Volleyball, title: 'Activities and programs', text: 'Sport, creative, study and social activities.' },
	location: { icon: MapPin, title: 'Convenient location', text: 'On or near school grounds, easy to reach.' },
	homework: { icon: BookOpen, title: 'Homework support', text: 'A quiet space and help with homework.' },
	food: { icon: Apple, title: 'Afternoon tea', text: 'Healthy food to keep them going.' },
	staff: { icon: BadgeCheck, title: 'Qualified staff', text: 'Experienced, checked and trained staff.' },
	booking: { icon: CalendarCheck, title: 'Easy online booking', text: 'Book and pay for sessions online.' }
};

export const HIGHLIGHT_ICONS = Object.keys(HIGHLIGHT_PRESETS) as HighlightIcon[];

// What the editor starts with before any are saved (nothing shows on the
// site until the owner saves).
export const SUGGESTED_HIGHLIGHTS: HighlightIcon[] = ['shield', 'community', 'activities', 'location'];

export function presetHighlight(icon: HighlightIcon): HighlightItem {
	const preset = HIGHLIGHT_PRESETS[icon];

	return { icon, title: preset.title, text: preset.text };
}
