import { error } from '@sveltejs/kit';

import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { createActionsApi } from '$lib/api/public/adapters/actions';
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

	const session =
		sessionResponse.ok && sessionResponse.data
			? {
					userId: sessionResponse.data.user_id,
					locationId: sessionResponse.data.location_id,
					email: sessionResponse.data.email,
					firstName: sessionResponse.data.first_name,
					roles: sessionResponse.data.roles
				}
			: null;

	// Resolve action count
	depends('app:actions-count');

	let uncitedActionCount = 0;

	if (session) {
		const actionsApi = createActionsApi(fetch);

		const actionCountResponse =
			await actionsApi.countUncited();

		uncitedActionCount =
			actionCountResponse.data ?? 0;
	}

	return {
		locationCode,
		location: locationResponse.data,
		session,
		uncitedActionCount
	};
};