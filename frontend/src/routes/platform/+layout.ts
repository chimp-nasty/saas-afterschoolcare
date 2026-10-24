import { error } from '@sveltejs/kit';

import { createPlatformApi } from '$lib/api/platform/adapters/platform';
import { isPlatformSite } from '$lib/platform/site';

import type { LayoutLoad } from './$types';

// The platform console (/platform): its admins, on the platform's own site
// only (a tenant's site has none). Anyone without a platform login is sent
// to its login page.
export const load: LayoutLoad = async ({ depends, fetch, url }) => {
	if (!isPlatformSite(url)) {
		error(404, 'Not Found');
	}

	depends('app:platform-session');

	const response = await createPlatformApi(fetch).getSession();

	return {
		session: response.ok ? response.data : null
	};
};
