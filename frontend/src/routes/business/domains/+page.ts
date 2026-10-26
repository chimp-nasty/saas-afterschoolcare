import { createBusinessApi } from '$lib/api/tenancy/adapters/business';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:business-domains');

	const response = await createBusinessApi(fetch).domains();

	return {
		domains: response.data ?? null
	};
};
