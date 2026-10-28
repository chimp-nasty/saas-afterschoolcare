import { createChildrenApi } from '$lib/api/public/adapters/children';
import { createPickupsApi } from '$lib/api/public/adapters/pickups';

import type { PageLoad } from './$types';

// Whether the family has pickup people besides the account holder: then
// adding a child needs their consent (everyone on the list may collect them).
// And whether this is their first child, which emails them a kiosk PIN
// (the page then says so).
export const load: PageLoad = async ({ fetch }) => {
	const [pickupsResponse, childrenResponse] = await Promise.all([
		createPickupsApi(fetch).list(),
		createChildrenApi(fetch).list({ is_active: true })
	]);

	return {
		hasOtherPickups: (pickupsResponse.data ?? []).some(
			(pickup) => !pickup.is_account_holder
		),
		isFirstChild: (childrenResponse.data ?? []).length === 0
	};
};
