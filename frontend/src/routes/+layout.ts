import { createPlatformApi } from '$lib/api/platform/adapters/platform';
import { createPlatformSiteApi } from '$lib/api/platform/adapters/platformSite';
import { isPlatformSite } from '$lib/platform/site';

import type { LayoutLoad } from './$types';

// A single-page app: nothing renders on the server (adapter-static with a
// fallback page; the API is on the same site under /api).
export const ssr = false;

// On the platform's own site, every page (the landing page, contact,
// registration, the console, errors) has the platform's branding and
// knows whether a platform admin is logged in (the header's Platform link
// and editing the landing page in place: docs/platform-site.md). A
// business's site has neither.
export const load: LayoutLoad = async ({ depends, fetch, url, untrack }) => {
	// The host never changes within the app: don't reload on every page.
	if (!untrack(() => isPlatformSite(url))) {
		return { platformSite: null, isPlatformAdmin: false };
	}

	depends('app:platform-site');
	depends('app:platform-session');

	const [site, session] = await Promise.all([
		createPlatformSiteApi(fetch).get(),
		createPlatformApi(fetch).getSession()
	]);

	return {
		platformSite: site.data ?? null,
		isPlatformAdmin: session.ok
	};
};
