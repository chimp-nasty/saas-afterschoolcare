import { createBusinessApi } from '$lib/api/tenancy/adapters/business';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:business');

	const response = await createBusinessApi(fetch).locations();

	return {
		locations: response.data ?? []
	};
};
