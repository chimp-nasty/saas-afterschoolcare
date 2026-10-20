export const accountTabs = {
	PROFILE: 'profile',
	CHILDREN: 'children',
	PICKUPS: 'pickups'
} as const;

export const childTabs = {
	PROFILE: 'profile',
	MANAGE_DOCUMENTS: 'manage-documents'
} as const;

// Match the backend's BookingGroupScope values: each tab is also the
// `scope` it lists.
export const bookingTabs = {
	UPCOMING: 'upcoming',
	HISTORY: 'history'
} as const;

export const actionTabs = {
	NEW: 'new',
	OLDER: 'older'
} as const;

// Staff medical review list: waiting on staff, or on the family.
export const reviewTabs = {
	PENDING: 'pending',
	REQUESTED: 'requested'
} as const;

export type AccountTab =
	typeof accountTabs[keyof typeof accountTabs];

export type ChildTab =
	typeof childTabs[keyof typeof childTabs];

export type BookingTab =
	typeof bookingTabs[keyof typeof bookingTabs];

export type ActionTab =
	typeof actionTabs[keyof typeof actionTabs];