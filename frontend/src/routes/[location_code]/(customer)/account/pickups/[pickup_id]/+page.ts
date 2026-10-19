import { error } from '@sveltejs/kit';

import { createPickupsApi } from '$lib/api/public/adapters/pickups';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	params
}) => {
	depends('app:pickup');

	const pickupsApi = createPickupsApi(fetch);

	const pickupResponse = await pickupsApi.getById(params.pickup_id);

	// The account holder's own row is edited through their profile.
	if (!pickupResponse.ok || !pickupResponse.data || pickupResponse.data.is_account_holder) {
		error(404, 'Pickup person not found');
	}

	return {
		pickup: pickupResponse.data
	};
};
