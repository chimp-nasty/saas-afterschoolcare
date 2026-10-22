import { createStaffAccountsApi } from '$lib/api/auth/adapters/staffAccounts';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch
}) => {
	depends('app:staff-accounts');

	const response = await createStaffAccountsApi(fetch).list();

	return {
		staff: response.data ?? []
	};
};
