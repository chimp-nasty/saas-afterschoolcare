import { createPickupsApi } from '$lib/api/public/adapters/pickups';

import type { PageLoad } from './$types';

// Whether the family has pickup people besides the account holder: then
// adding a child needs their consent (everyone on the list may collect them).
export const load: PageLoad = async ({ fetch }) => {
	const pickupsResponse = await createPickupsApi(fetch).list();

	return {
		hasOtherPickups: (pickupsResponse.data ?? []).some(
			(pickup) => !pickup.is_account_holder
		)
	};
};
