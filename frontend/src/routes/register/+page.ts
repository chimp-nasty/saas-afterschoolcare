import { error } from '@sveltejs/kit';

import { createRegistrationApi } from '$lib/api/platform/adapters/platform';
import { isPlatformSite } from '$lib/platform/site';

import type { PageLoad } from './$types';

// Registering a business with its invite (?invite=…), on the platform's
// own site only. The invite says whose email the owner's login will be.
export const load: PageLoad = async ({ fetch, url }) => {
	if (!isPlatformSite(url)) {
		error(404, 'Not Found');
	}

	const token = url.searchParams.get('invite');

	if (!token) {
		return { token: null, email: null };
	}

	const response = await createRegistrationApi(fetch).invite(token);

	return {
		token,
		email: response.ok && response.data ? response.data.email : null
	};
};
