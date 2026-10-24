import { createBusinessApi } from '$lib/api/tenancy/adapters/business';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:business-site');

	const response = await createBusinessApi(fetch).site();

	return {
		site: response.data ?? null
	};
};
