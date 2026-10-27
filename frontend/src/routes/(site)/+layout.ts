import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';
import { isBusinessOwner } from '$lib/navigation/siteLinks';
import { isPlatformSite } from '$lib/platform/site';

import type { LayoutLoad } from './$types';

// The business's pages (/, /locations, /about: docs/public-site.md): its
// words, branding and FAQs, and its centres, found from the site's address,
// and whether the visitor is its owner (logged in here or at a centre), for
// the Business link. On the platform's own site there's no business: /
// gets a placeholder.
export const load: LayoutLoad = async ({ depends, fetch, url }) => {
	depends('app:session');

	if (isPlatformSite(url)) {
		return { platform: true, business: null, locations: [], isOwner: false };
	}

	const api = createLocationBrandingApi(fetch);

	const [businessResponse, locationsResponse, sessionResponse] = await Promise.all([
		api.getPublicBusiness(),
		api.listPublicLocations(),
		createAuthApi(fetch).getSession()
	]);

	return {
		platform: false,
		business: businessResponse.data ?? null,
		locations: locationsResponse.data ?? [],
		isOwner: sessionResponse.ok && isBusinessOwner(sessionResponse.data?.tenant_permissions)
	};
};
