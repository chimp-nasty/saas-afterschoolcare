import type { CustomerProfileResponse, EmergencyRelation } from '$lib/api/schema';

// How a family's emergency contact is related to them (not a pickup relation).
export const EMERGENCY_RELATION_LABELS: Record<EmergencyRelation, string> = {
	parent_guardian: 'Other parent or guardian',
	grandparent: 'Grandparent',
	aunt_uncle: 'Aunt or uncle',
	family_friend: 'Family friend',
	neighbour: 'Neighbour',
	nanny_babysitter: 'Nanny or babysitter',
	other: 'Other'
};

type EmergencyContact = {
	emergency_contact_relation: string | null;
	emergency_contact_relation_other: string | null;
};

// "Other" shows what the family typed instead.
export function emergencyRelationLabel(contact: EmergencyContact): string {
	const relation = contact.emergency_contact_relation;

	if (!relation) return '—';

	if (relation === 'other') return contact.emergency_contact_relation_other ?? 'Other';

	return EMERGENCY_RELATION_LABELS[relation as EmergencyRelation] ?? relation;
}

// Booking needs one (the backend's missing "emergency_contact").
export function hasEmergencyContact(profile: CustomerProfileResponse): boolean {
	return !!(profile.emergency_contact_name && profile.emergency_contact_phone && profile.emergency_contact_relation);
}

// What booking still needs from the profile, in words ("your phone
// number", "an emergency contact"); empty when it's complete (the
// backend's get_missing_profile_fields).
export function missingForBooking(profile: CustomerProfileResponse): string[] {
	const missing: string[] = [];

	if (!profile.phone) missing.push('your phone number');
	if (!(profile.address_line_1 && profile.suburb && profile.state && profile.postcode)) missing.push('your address');
	if (!hasEmergencyContact(profile)) missing.push('an emergency contact');

	return missing;
}
