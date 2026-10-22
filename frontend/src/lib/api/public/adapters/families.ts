import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type {
	ChildNoteResponse,
	CreateChildNoteRequest,
	FamilyAttendanceResponse,
	FamilyBookingResponse,
	FamilyMessageResponse,
	FamilyPaymentResponse,
	FamilyResponse,
	FamilySearchResultResponse,
	SendFamilyMessageRequest,
	UpdateContactDetailsRequest
} from '$lib/api/schema';


// Admin › Families: this centre's families (admins and superadmins).
export function createFamiliesApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/families/v1`;

	const dated = (path: string, dateFrom?: string | null, dateTo?: string | null) => {
		const query = buildQueryParams({ date_from: dateFrom ?? undefined, date_to: dateTo ?? undefined });

		return `${baseUrl}${path}${query ? `?${query}` : ''}`;
	};

	return {
		// A child's or parent's name, an email or a phone (2+ characters).
		search(q: string) {
			return apiWrapper<FamilySearchResultResponse[]>(`${baseUrl}/?${buildQueryParams({ q })}`, {
				method: 'GET',
				fetcher
			});
		},

		get(userId: string) {
			return apiWrapper<FamilyResponse>(`${baseUrl}/${userId}`, { method: 'GET', fetcher });
		},

		// Phone and address.
		update(userId: string, body: UpdateContactDetailsRequest) {
			return apiWrapper<FamilyResponse>(`${baseUrl}/${userId}`, { method: 'PATCH', body, fetcher });
		},

		// Default: a month back to three ahead, plus anything unpaid.
		bookings(userId: string, dateFrom?: string | null, dateTo?: string | null) {
			return apiWrapper<FamilyBookingResponse[]>(dated(`/${userId}/bookings`, dateFrom, dateTo), {
				method: 'GET',
				fetcher
			});
		},

		// Default: the last 4 weeks.
		attendance(userId: string, dateFrom?: string | null, dateTo?: string | null) {
			return apiWrapper<FamilyAttendanceResponse[]>(dated(`/${userId}/attendance`, dateFrom, dateTo), {
				method: 'GET',
				fetcher
			});
		},

		payments(userId: string) {
			return apiWrapper<FamilyPaymentResponse[]>(`${baseUrl}/${userId}/payments`, { method: 'GET', fetcher });
		},

		// Staff's notes about the children (never shown to the family).
		notes(userId: string) {
			return apiWrapper<ChildNoteResponse[]>(`${baseUrl}/${userId}/notes`, { method: 'GET', fetcher });
		},

		addNote(userId: string, body: CreateChildNoteRequest) {
			return apiWrapper<ChildNoteResponse>(`${baseUrl}/${userId}/notes`, { method: 'POST', body, fetcher });
		},

		deleteNote(userId: string, noteId: string) {
			return apiWrapper<null>(`${baseUrl}/${userId}/notes/${noteId}`, { method: 'DELETE', fetcher });
		},

		// Messages to the family, read in their account.
		messages(userId: string) {
			return apiWrapper<FamilyMessageResponse[]>(`${baseUrl}/${userId}/messages`, { method: 'GET', fetcher });
		},

		sendMessage(userId: string, body: SendFamilyMessageRequest) {
			return apiWrapper<FamilyMessageResponse>(`${baseUrl}/${userId}/messages`, { method: 'POST', body, fetcher });
		},

		withdrawMessage(userId: string, messageId: string) {
			return apiWrapper<null>(`${baseUrl}/${userId}/messages/${messageId}`, { method: 'DELETE', fetcher });
		}
	};
}
