import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type {
	ActionPlanResponse,
	AttendanceTimesResponse,
	ChildDocumentDownloadResponse,
	ChildMedicalResponse,
	ChildNoteResponse,
	ChildSearchResultResponse,
	FamilyBookingResponse,
	RefundResponse,
	KioskInfoResponse,
	RollPickupPersonResponse,
	RollResponse,
	RunSheetResponse,
	StaffKioskBulkRequest,
	StaffKioskMemberResponse,
	StaffKioskSignRequest,
	StaffKioskVerifyResponse,
	StaffShiftResponse
} from '$lib/api/schema';

// The staff member doing the current task, and the PIN they entered for it.
// Kept in memory for that one task only (docs/portals.md): nobody is ever
// logged in at the staff kiosk.
export type StaffCredentials = {
	userId: string;
	pin: string;
};

// The staff kiosk. The tablet's device cookie alone shows the staff list
// and the run sheet without personal details; everything else carries a
// staff member and their PIN. Silent: the kiosk shows outcomes on screen.
export function createStaffKioskApi(locationCode: string) {
	const baseUrl = `${API_BASE}/staff-kiosk/v1/${locationCode}`;
	const as = (staff: StaffCredentials) => ({ 'X-Kiosk-Staff': staff.userId, 'X-Kiosk-Pin': staff.pin });
	const dated = (path: string, date?: string) => {
		const query = buildQueryParams({ date });

		return `${baseUrl}${path}${query ? `?${query}` : ''}`;
	};

	return {
		device() {
			return apiWrapper<KioskInfoResponse>(`${baseUrl}/device`, { silent: true });
		},

		staff() {
			return apiWrapper<StaffKioskMemberResponse[]>(`${baseUrl}/staff`, { silent: true });
		},

		board(date?: string) {
			return apiWrapper<RunSheetResponse>(dated('/board', date), { silent: true });
		},

		verify(staff: StaffCredentials) {
			return apiWrapper<StaffKioskVerifyResponse>(`${baseUrl}/verify`, {
				method: 'POST',
				headers: as(staff),
				silent: true
			});
		},

		roll(staff: StaffCredentials, date?: string) {
			return apiWrapper<RollResponse>(dated('/roll', date), { headers: as(staff), silent: true });
		},

		// sent_to_school defaults to false (before school care sets it).
		sign(staff: StaffCredentials, body: Omit<StaffKioskSignRequest, 'sent_to_school'> & { sent_to_school?: boolean }) {
			return apiWrapper<AttendanceTimesResponse>(`${baseUrl}/sign`, {
				method: 'POST',
				body: { sent_to_school: false, ...body },
				headers: as(staff),
				silent: true
			});
		},

		// Several children at once, all or nothing: a session's arrivals, a
		// before school session sent to school, or brothers and sisters signed
		// out to the same person (`out`: the collector or one-off release).
		bulk(
			staff: StaffCredentials,
			action: StaffKioskBulkRequest['action'],
			bookingIds: string[],
			at: string | null,
			out: Pick<StaffKioskBulkRequest, 'collected_by_pickup_person_id' | 'released_to_name' | 'release_note'> = {}
		) {
			return apiWrapper<AttendanceTimesResponse[]>(`${baseUrl}/bulk`, {
				method: 'POST',
				body: { action, booking_ids: bookingIds, at, ...out },
				headers: as(staff),
				silent: true
			});
		},

		// Find a family by a child's name (at least 2 letters).
		searchChildren(staff: StaffCredentials, text: string) {
			const query = buildQueryParams({ q: text });

			return apiWrapper<ChildSearchResultResponse[]>(`${baseUrl}/children/search?${query}`, {
				headers: as(staff),
				silent: true
			});
		},

		// A family's bookings: today to 2 weeks ahead, and anything unpaid.
		familyBookings(staff: StaffCredentials, familyUserId: string) {
			return apiWrapper<FamilyBookingResponse[]>(`${baseUrl}/families/${familyUserId}/bookings`, {
				headers: as(staff),
				silent: true
			});
		},

		// Refund one booking in full (admins only).
		refund(staff: StaffCredentials, bookingId: string) {
			return apiWrapper<RefundResponse>(`${baseUrl}/refunds`, {
				method: 'POST',
				body: { booking_id: bookingId },
				headers: as(staff),
				silent: true
			});
		},

		medical(staff: StaffCredentials, childId: string) {
			return apiWrapper<ChildMedicalResponse>(`${baseUrl}/children/${childId}/medical`, {
				headers: as(staff),
				silent: true
			});
		},

		// Staff's notes about the child (written by admins on the website).
		notes(staff: StaffCredentials, childId: string) {
			return apiWrapper<ChildNoteResponse[]>(`${baseUrl}/children/${childId}/notes`, {
				headers: as(staff),
				silent: true
			});
		},

		actionPlans(staff: StaffCredentials) {
			return apiWrapper<ActionPlanResponse[]>(`${baseUrl}/action-plans`, { headers: as(staff), silent: true });
		},

		// A short-lived link to view or print the file.
		download(staff: StaffCredentials, documentId: string) {
			return apiWrapper<ChildDocumentDownloadResponse>(`${baseUrl}/documents/${documentId}/download`, {
				headers: as(staff),
				silent: true
			});
		},

		// Tick (or untick) that a plan's been printed for the folder.
		setPrinted(staff: StaffCredentials, documentId: string, printed: boolean) {
			return apiWrapper<null>(`${baseUrl}/documents/${documentId}/printed`, {
				method: 'PUT',
				body: { printed },
				headers: as(staff),
				silent: true
			});
		},

		undo(staff: StaffCredentials, bookingId: string, step: 'sign_in' | 'sign_out') {
			return apiWrapper<AttendanceTimesResponse>(`${baseUrl}/undo`, {
				method: 'POST',
				body: { booking_id: bookingId, step },
				headers: as(staff),
				silent: true
			});
		},

		checkId(staff: StaffCredentials, pickupPersonId: string, idSeen: boolean) {
			return apiWrapper<RollPickupPersonResponse>(`${baseUrl}/check-id`, {
				method: 'POST',
				body: { pickup_person_id: pickupPersonId, id_seen: idSeen },
				headers: as(staff),
				silent: true
			});
		},

		// Clocking in after a forgotten clock-out says when they left it.
		shift(staff: StaffCredentials, action: 'start' | 'end', previousShiftEndedAt?: string) {
			return apiWrapper<StaffShiftResponse>(`${baseUrl}/shift`, {
				method: 'POST',
				body: { action, previous_shift_ended_at: previousShiftEndedAt ?? null },
				headers: as(staff),
				silent: true
			});
		}
	};
}
