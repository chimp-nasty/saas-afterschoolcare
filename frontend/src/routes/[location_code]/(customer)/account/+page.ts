import { error } from '@sveltejs/kit';

import { createCustomerApi } from '$lib/api/public/adapters/customer';
import { createChildrenApi } from '$lib/api/public/adapters/children';
import { createPickupsApi } from '$lib/api/public/adapters/pickups';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	const customerApi = createCustomerApi(fetch);
	const childrenApi = createChildrenApi(fetch);
	const pickupsApi = createPickupsApi(fetch);

	const [
		customerProfileResponse,
		childProfileResponse,
		pickupsResponse,
	] = await Promise.all([
		customerApi.getProfile(),
		childrenApi.list({
			is_active: true
		}),
		pickupsApi.list()
	]);

	if (
		!customerProfileResponse.ok ||
		!customerProfileResponse.data
	) {
		error(500, 'Customer profile could not be loaded');
	}

	depends('app:customer-account');

	return {
		customerProfile: customerProfileResponse.data,
		
		childProfiles: childProfileResponse.data ?? [],

		pickups: pickupsResponse.data ?? [],
	};
};