import { createFamiliesApi } from '$lib/api/public/adapters/families';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	fetch,
	url
}) => {
	// ?q= what was searched (2+ characters).
	const q = (url.searchParams.get('q') ?? '').trim();
	const response = q.length >= 2 ? await createFamiliesApi(fetch).search(q) : null;

	return {
		q,
		families: response?.data ?? null
	};
};
