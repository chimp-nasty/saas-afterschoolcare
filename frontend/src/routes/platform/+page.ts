import { createPlatformApi } from '$lib/api/platform/adapters/platform';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:platform-tenants');

	const response = await createPlatformApi(fetch).tenants();

	return {
		tenants: response.data ?? []
	};
};
