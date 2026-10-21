import { createAccountApi } from '$lib/api/auth/adapters/account';
import { createStaffPinApi } from '$lib/api/auth/adapters/staffPin';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	depends('app:staff-pin');

	const [accountResponse, pinResponse] = await Promise.all([
		createAccountApi(fetch).get(),
		createStaffPinApi(fetch).status()
	]);

	return {
		account: accountResponse.data,
		status: pinResponse.data
	};
};
