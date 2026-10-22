import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { PublicLocationResponse } from '$lib/api/schema';


export function createLocationBrandingApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/location-branding/v1`;

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
