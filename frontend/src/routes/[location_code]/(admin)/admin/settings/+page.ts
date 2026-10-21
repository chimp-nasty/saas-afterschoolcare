import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	depends('app:service-settings');

	const response = await createLocationServicesApi(fetch).settings();

	return {
		services: response.data ?? []
	};
};
