export const accountTabs = {
	PROFILE: 'profile',
	CHILDREN: 'children'
} as const;

export const childTabs = {
	PROFILE: 'profile',
	AUTHORIZED_PICKUPS: 'authorized-pickups',
	MANAGE_DOCUMENTS: 'manage-documents'
} as const;

export const actionTabs = {
	NEW: 'new',
	OLDER: 'older'
} as const;

export type AccountTab =
	typeof accountTabs[keyof typeof accountTabs];

export type ChildTab =
	typeof childTabs[keyof typeof childTabs];

export type ActionTab =
	typeof actionTabs[keyof typeof actionTabs];