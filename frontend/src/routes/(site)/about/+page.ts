import { redirect } from '@sveltejs/kit';

import type { PageLoad } from './$types';

// The business's own page: nothing to show on the platform's site.
export const load: PageLoad = async ({ parent }) => {
	if ((await parent()).platform) {
		redirect(307, '/');
	}
};
