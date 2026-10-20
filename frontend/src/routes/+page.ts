import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';

import type { PageLoad } from './$types';

export const ssr = false;

// The tenant's centres, found from the site's address. A placeholder until
// tenant setup gives this page its own content.
export const load: PageLoad = async ({ fetch }) => {
	const locationsResponse = await createLocationBrandingApi(fetch).listPublicLocations();

	return {
		locations: locationsResponse.data ?? []
	};
};
