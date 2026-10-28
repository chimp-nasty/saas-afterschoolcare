import { error } from '@sveltejs/kit';

import { createCustomerApi } from '$lib/api/public/adapters/customer';
import { createChildrenApi } from '$lib/api/public/adapters/children';
import { createPickupsApi } from '$lib/api/public/adapters/pickups';

import type { PageLoad } from './$types';

// What the family has added so far: each step saves as it goes, so the
// wizard picks up where they left off.
export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:customer-account');

	const [profileResponse, childrenResponse, pickupsResponse] = await Promise.all([
		createCustomerApi(fetch).getProfile(),
		createChildrenApi(fetch).list({ is_active: true }),
		createPickupsApi(fetch).list()
	]);

	if (!profileResponse.ok || !profileResponse.data) {
		error(500, 'Customer profile could not be loaded');
	}

	return {
		profile: profileResponse.data,
		children: childrenResponse.data ?? [],
		pickups: pickupsResponse.data ?? []
	};
};
