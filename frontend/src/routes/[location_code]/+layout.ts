import { error } from '@sveltejs/kit';

import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';

import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({
	params,
	depends,
	fetch
}) => {
	if (!params.location_code) {
		throw new Error('Location code is required');
	}

	const locationCode = params.location_code;

	// Resolve location
	const brandingApi = createLocationBrandingApi(fetch);

	const locationResponse =
		await brandingApi.getPublicLocation(locationCode);

	if (!locationResponse.ok || !locationResponse.data) {
		error(404, 'Not Found');
	}

	// Resolve session
	depends('app:session');

	const authApi = createAuthApi(fetch);

	const sessionResponse =
		await authApi.getSession();

	return {
		locationCode,

		location: locationResponse.data,

		session:
			sessionResponse.ok && sessionResponse.data
				? {
						userId: sessionResponse.data.user_id,
						locationId: sessionResponse.data.location_id,
						email: sessionResponse.data.email,
						firstName: sessionResponse.data.first_name,
						roles: sessionResponse.data.roles
					}
				: null
	};
};