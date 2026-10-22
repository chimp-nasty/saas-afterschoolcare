import { createActionsApi } from '$lib/api/public/adapters/actions';

import type { PageLoad } from './$types';

// How many of each list show at first, and how many more "Show more" adds
// (the underscore lets the page import it; SvelteKit reserves other exports).
export const _PAGE_SIZE = 10;

function shown(url: URL, key: string): number {
	const value = Number(url.searchParams.get(key));

	return Number.isInteger(value) && value > 0 ? Math.min(value, 100) : _PAGE_SIZE;
}

export const load: PageLoad = async ({ depends, fetch, url }) => {
	depends('app:actions');

	const api = createActionsApi(fetch);
	// "Show more" raises how many are shown (kept in the address), up to the
	// API's 100 per page.
	const newShown = shown(url, 'new_shown');
	const readShown = shown(url, 'read_shown');

	const [unread, read] = await Promise.all([
		api.list({ cited: false }, { page: 1, limit: newShown }),
		api.list({ cited: true }, { page: 1, limit: readShown })
	]);

	return {
		unread: unread.data ?? [],
		read: read.data ?? [],
		newShown,
		readShown
	};
};
