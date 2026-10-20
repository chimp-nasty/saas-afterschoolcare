import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';

import type { PageLoad } from './$types';

// The landing page works before login: the location's offered services are
// public (the location itself comes from the layout).
export const load: PageLoad = async ({ fetch, params }) => {
	const servicesResponse = await createLocationServicesApi(fetch).listPublic(params.location_code);

	return {
		services: servicesResponse.data ?? []
	};
};
