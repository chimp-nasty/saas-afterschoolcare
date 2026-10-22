import { createStripeAccountApi } from '$lib/api/tenancy/adapters/stripeAccount';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	depends('app:stripe-account');

	const response = await createStripeAccountApi(fetch).status();

	return {
		account: response.data ?? null
	};
};
