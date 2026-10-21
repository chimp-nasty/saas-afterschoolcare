// The two kinds of kiosk tablet a location has (one active of each), as
// Admin › Kiosks describes them.
export type KioskKind = 'family' | 'staff';

export const KIOSK_KINDS: Record<KioskKind, { label: string; defaultName: string; description: string }> = {
	family: {
		label: 'Family kiosk',
		defaultName: 'Front entrance',
		description: 'At the entrance: parents and pickup people sign their children in and out with their mobile and PIN.'
	},
	staff: {
		label: 'Staff kiosk',
		defaultName: 'Staff tablet',
		description: 'For staff: clocking in and out, the run sheet, signing children in and out, and checking ID.'
	}
};
