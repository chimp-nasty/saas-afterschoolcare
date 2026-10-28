import { createPlatformEnquiriesApi } from '$lib/api/platform/adapters/platformEnquiries';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({ depends, fetch }) => {
	depends('app:platform-enquiries');

	const api = createPlatformEnquiriesApi(fetch);
	const [open, closed] = await Promise.all([api.list(false), api.list(true)]);

	return {
		open: open.data ?? [],
		closed: closed.data ?? []
	};
};
