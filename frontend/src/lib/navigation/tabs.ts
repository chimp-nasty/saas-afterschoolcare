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
	READ: 'read'
} as const;

// The staff kiosk (docs/portals.md).
export const kioskTabs = {
	RUN_SHEET: 'run-sheet',
	SHIFTS: 'shifts',
	MEDICAL: 'medical',
	ADMIN: 'admin'
} as const;

// Admin › Families › a family.
export const familyTabs = {
	DETAILS: 'details',
	BOOKINGS: 'bookings',
	ATTENDANCE: 'attendance',
	PAYMENTS: 'payments',
	NOTES: 'notes',
	MESSAGES: 'messages'
} as const;

// A child's task window at the staff kiosk.
export const kioskChildTabs = {
	ATTENDANCE: 'attendance',
	MEDICAL: 'medical',
	NOTES: 'notes',
	BOOKINGS: 'bookings'
} as const;

// Staff medical review list: waiting on staff, or on the family.
export const reviewTabs = {
	PENDING: 'pending',
	REQUESTED: 'requested',
	APPROVED: 'approved'
} as const;

export type AccountTab =
	typeof accountTabs[keyof typeof accountTabs];

export type ChildTab =
	typeof childTabs[keyof typeof childTabs];

export type BookingTab =
	typeof bookingTabs[keyof typeof bookingTabs];

export type ActionTab =
	typeof actionTabs[keyof typeof actionTabs];