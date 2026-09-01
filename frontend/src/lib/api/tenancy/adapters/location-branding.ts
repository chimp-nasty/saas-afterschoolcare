import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { PublicLocationResponse } from '../types/location-branding';


export function createLocationBrandingApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/location-branding/v1`;

	return {
		getPublicLocation(locationCode: string) {
			return apiWrapper<PublicLocationResponse>(
				`${baseUrl}/public/${locationCode}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},
	};
}