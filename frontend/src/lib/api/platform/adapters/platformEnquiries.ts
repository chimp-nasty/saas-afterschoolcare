import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type { PlatformEnquiryResponse, SubmitPlatformEnquiryRequest } from '$lib/api/schema';


// Enquiries to the platform itself (docs/platform-site.md): anyone sends
// one from the contact page; the platform's admins read and close them.
export function createPlatformEnquiriesApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/platform-enquiries/v1`;

	return {
		submit(body: SubmitPlatformEnquiryRequest) {
			return apiWrapper<null>(`${baseUrl}/`, { method: 'POST', body, fetcher });
		},

		list(closed = false) {
			return apiWrapper<PlatformEnquiryResponse[]>(`${baseUrl}/?closed=${closed}`, { method: 'GET', fetcher });
		},

		close(id: string) {
			return apiWrapper<PlatformEnquiryResponse>(`${baseUrl}/${id}/close`, { method: 'POST', fetcher });
		},

		reopen(id: string) {
			return apiWrapper<PlatformEnquiryResponse>(`${baseUrl}/${id}/reopen`, { method: 'POST', fetcher });
		}
	};
}
