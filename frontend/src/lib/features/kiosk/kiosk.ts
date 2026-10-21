import type { ApiResponse } from '$lib/api/wrapper';

// docs/kiosk-procedures.md, section 1: a person's session ends after 60
// seconds without a tap, and 10 seconds after they sign a child in or out
// (any tap resets that).
export const SESSION_IDLE_MS = 60_000;
export const DONE_LOGOUT_MS = 10_000;

// How often the staff kiosk's roll refreshes itself.
export const ROLL_REFRESH_MS = 20_000;

// "5:42pm" for an ISO timestamp, in the tablet's own timezone (it's at the
// centre).
export function formatClock(value: string): string {
	return new Date(value)
		.toLocaleTimeString('en-AU', { hour: 'numeric', minute: '2-digit', hour12: true })
		.replace(/\s/g, '')
		.toLowerCase();
}

// "0412 345 678" while it's being typed (up to 10 digits).
export function formatTypedPhone(digits: string): string {
	return [digits.slice(0, 4), digits.slice(4, 7), digits.slice(7, 10)].filter(Boolean).join(' ');
}

// What to show for a failed call: the field's message for a 422, else the
// API's message.
export function messageOf(response: ApiResponse<unknown>): string {
	const fieldMessage = Object.values(response.fieldErrors)[0];

	return fieldMessage ?? response.msg ?? 'Something went wrong. Please try again.';
}

// A timer that fires `onTimeout` after `ms` unless reset; the kiosk resets
// it on every tap.
export function createTimer(ms: number, onTimeout: () => void) {
	let handle: ReturnType<typeof setTimeout> | null = null;

	return {
		reset() {
			if (handle) clearTimeout(handle);
			handle = setTimeout(onTimeout, ms);
		},
		stop() {
			if (handle) clearTimeout(handle);
			handle = null;
		}
	};
}

// Someone who clocked out today at this tablet (the Shifts tab).
export type ClockedOut = {
	userId: string;
	name: string;
	startedAt: string | null;
	endedAt: string;
};

// Today's clock-outs are kept on the tablet, per location and day: the
// staff list only has open shifts. There's one staff kiosk per location,
// so it's normally complete, but it's a convenience, not a record (the
// shifts themselves are in the database).
function clockedOutKey(locationCode: string, day: string): string {
	return `staff-kiosk:clocked-out:${locationCode}:${day}`;
}

export function readClockedOut(locationCode: string, day: string): ClockedOut[] {
	try {
		const raw = localStorage.getItem(clockedOutKey(locationCode, day));

		return raw ? (JSON.parse(raw) as ClockedOut[]) : [];
	} catch {
		return [];
	}
}

export function saveClockedOut(locationCode: string, day: string, shifts: ClockedOut[]): void {
	try {
		localStorage.setItem(clockedOutKey(locationCode, day), JSON.stringify(shifts));
	} catch {
		// Storage unavailable: the list just won't survive a reload.
	}
}
