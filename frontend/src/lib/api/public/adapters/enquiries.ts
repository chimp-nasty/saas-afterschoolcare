import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	EnquiryReplyRequest,
	EnquiryResponse,
	EnquirySummaryResponse,
	SubmitEnquiryRequest
} from '$lib/api/schema';


// Which enquiries the inbox lists: open is new and replied.
export type EnquiryStatusFilter = 'open' | 'new' | 'replied' | 'closed' | 'all';


// Contact form enquiries (docs/enquiries.md): anyone sends one from the
// centre's page; the centre's admins read, reply to, close and reopen them.
export function createEnquiriesApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/enquiries/v1`;

	return {
		submit(locationCode: string, body: SubmitEnquiryRequest) {
			return apiWrapper<null>(`${baseUrl}/${locationCode}/submit`, { method: 'POST', body, fetcher });
		},

		list(status: EnquiryStatusFilter = 'open') {
			return apiWrapper<EnquirySummaryResponse[]>(`${baseUrl}/?status=${status}`, { method: 'GET', fetcher });
		},

		get(id: string) {
			return apiWrapper<EnquiryResponse>(`${baseUrl}/${id}`, { method: 'GET', fetcher });
		},

		reply(id: string, body: EnquiryReplyRequest) {
			return apiWrapper<EnquiryResponse>(`${baseUrl}/${id}/reply`, { method: 'POST', body, fetcher });
		},

		close(id: string) {
			return apiWrapper<EnquiryResponse>(`${baseUrl}/${id}/close`, { method: 'POST', fetcher });
		},

		reopen(id: string) {
			return apiWrapper<EnquiryResponse>(`${baseUrl}/${id}/reopen`, { method: 'POST', fetcher });
		}
	};
}
