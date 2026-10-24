import { createPlatformApi } from '$lib/api/platform/adapters/platform';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:platform-invites');

	const response = await createPlatformApi(fetch).invites();

	return {
		invites: response.data ?? []
	};
};
