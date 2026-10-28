import type { CustomerProfileResponse } from '$lib/api/schema';

import { hasEmergencyContact } from './emergency';

// The setup wizard's steps (/{location}/setup), in order, then its last
// screen. Pickup people are optional; the other three are what booking
// needs (missingForBooking), so they're what "done" counts.
export const SETUP_STEPS = ['details', 'emergency', 'children', 'pickups'] as const;

export type SetupStep = (typeof SETUP_STEPS)[number] | 'done';

export const SETUP_STEP_TITLES: Record<(typeof SETUP_STEPS)[number], string> = {
	details: 'Your details',
	emergency: 'Emergency contact',
	children: 'Your children',
	pickups: 'Who can collect'
};

export function hasContactDetails(profile: CustomerProfileResponse): boolean {
	return !!(profile.phone && profile.address_line_1 && profile.suburb && profile.state && profile.postcode);
}

export type SetupProgress = {
	details: boolean;
	emergency: boolean;
	children: boolean;
	// Of the three required steps.
	done: number;
	total: number;
	// The first required step still to do, or null when setup is finished.
	next: SetupStep | null;
};

export function setupProgress(profile: CustomerProfileResponse, childCount: number): SetupProgress {
	const steps = {
		details: hasContactDetails(profile),
		emergency: hasEmergencyContact(profile),
		children: childCount > 0
	};

	const required = ['details', 'emergency', 'children'] as const;

	return {
		...steps,
		done: required.filter((step) => steps[step]).length,
		total: required.length,
		next: required.find((step) => !steps[step]) ?? null
	};
}

export function setupHref(locationCode: string, step?: SetupStep): string {
	return `/${locationCode}/setup${step ? `?step=${step}` : ''}`;
}
