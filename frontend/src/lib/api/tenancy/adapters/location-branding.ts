import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type { PublicBusinessResponse, PublicLocationResponse } from '$lib/api/schema';


// The business's logo, site icon (its logo if none, else the platform's) and
// current policy PDFs: links that redirect to the file (stage 5).
export type SiteFileKind = 'logo' | 'icon' | 'privacy' | 'terms';

export function siteFileUrl(kind: SiteFileKind): string {
	return `${API_BASE}/location-branding/v1/site-files/${kind}`;
}


export function createLocationBrandingApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/location-branding/v1`;

	return {
		// The tenant's centres (from the site's address), before login.
		listPublicLocations() {
			return apiWrapper<PublicLocationResponse[]>(
				`${baseUrl}/public`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		// The business's landing page: its words, colours and FAQs, and which
		// images and policies it has.
		getPublicBusiness() {
			return apiWrapper<PublicBusinessResponse>(`${baseUrl}/public/business`, { method: 'GET', fetcher });
		},

		getPublicLocation(locationCode: string) {
			return apiWrapper<PublicLocationResponse>(
				`${baseUrl}/public/${locationCode}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		// Whether families can book and pay there now (the business's
		// Stripe account takes payments). Not cached, unlike the above.
		bookingsOpen(locationCode: string) {
			return apiWrapper<boolean>(`${baseUrl}/public/${locationCode}/bookings-open`, { method: 'GET', fetcher });
		},
	};
}
