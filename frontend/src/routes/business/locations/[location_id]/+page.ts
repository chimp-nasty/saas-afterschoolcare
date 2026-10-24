import { error } from '@sveltejs/kit';

import { createBusinessApi } from '$lib/api/tenancy/adapters/business';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch, params }) => {
	depends('app:business');

	const response = await createBusinessApi(fetch).locations();
	const location = response.data?.find((row) => row.id === params.location_id);

	if (response.ok && !location) {
		error(404, 'Not Found');
	}

	return {
		location: location ?? null
	};
};
