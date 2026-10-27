import { redirect } from '@sveltejs/kit';

import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';

import type { PageLoad } from './$types';

// Every centre with the services it offers (public, like its own page). One
// request per centre, all at once: a business has a handful.
export const load: PageLoad = async ({ fetch, parent }) => {
	const { platform, locations } = await parent();

	if (platform) {
		redirect(307, '/');
	}

	const api = createLocationServicesApi(fetch);

	const responses = await Promise.all(
		locations.map((location) => api.listPublic(location.location_code))
	);

	return {
		servicesByCentre: Object.fromEntries(
			locations.map((location, index) => [location.location_code, responses[index].data ?? []])
		)
	};
};
