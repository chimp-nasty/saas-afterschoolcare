import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';

import type { PageLoad } from './$types';

// The centre's programs (docs/public-site.md, section 4): its offered
// services with their program text. Public, like the centre's page.
export const load: PageLoad = async ({ depends, fetch, params }) => {
	// Saving a program inline refreshes this.
	depends('app:programs');

	const response = await createLocationServicesApi(fetch).listPublic(params.location_code);

	return {
		services: response.data ?? []
	};
};
