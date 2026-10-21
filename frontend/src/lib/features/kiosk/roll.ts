import type { RollEntryResponse, RollPickupPersonResponse } from '$lib/api/schema';

// Where a child's session is up to on the roll. Shared by the staff kiosk
// (its run sheet and child panels) and the website's read-only roll, so
// all say the same thing.
export type RollStatus = 'expected' | 'here' | 'late' | 'gone';

export const ROLL_STATUS_LABELS: Record<RollStatus, string> = {
	expected: 'Not here',
	here: 'Here',
	late: 'Late',
	gone: 'Gone'
};

export function rollStatus(entry: Pick<RollEntryResponse, 'signed_in_at' | 'signed_out_at' | 'is_late'>): RollStatus {
	if (entry.signed_out_at) return 'gone';
	if (entry.is_late) return 'late';
	if (entry.signed_in_at) return 'here';

	return 'expected';
}

// Whether staff have sighted a pickup person's photo ID. Someone approved
// without ID can still collect, but every sign-out says so until it's
// checked.
export type PickupIdStatus = 'sighted' | 'not_sighted' | 'not_approved';

export const PICKUP_ID_STATUS_LABELS: Record<PickupIdStatus, string> = {
	sighted: 'ID sighted',
	not_sighted: 'ID not sighted',
	not_approved: 'Not approved yet'
};

export function pickupIdStatus(
	person: Pick<RollPickupPersonResponse, 'identity_verified_at' | 'staff_approved_at'>
): PickupIdStatus {
	if (person.identity_verified_at) return 'sighted';
	if (person.staff_approved_at) return 'not_sighted';

	return 'not_approved';
}
