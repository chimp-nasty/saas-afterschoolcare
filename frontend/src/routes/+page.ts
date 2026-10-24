import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';
import { isPlatformSite } from '$lib/platform/site';

import type { PageLoad } from './$types';

export const ssr = false;

// The business's landing page (stage 5): its words, branding and FAQs, and
// its centres, found from the site's address. On the platform's own site
// there's no business: it gets its own placeholder.
export const load: PageLoad = async ({ fetch, url }) => {
	if (isPlatformSite(url)) {
		return { platform: true, business: null, locations: [] };
	}

	const api = createLocationBrandingApi(fetch);

	const [businessResponse, locationsResponse] = await Promise.all([
		api.getPublicBusiness(),
		api.listPublicLocations()
	]);

	return {
		platform: false,
		business: businessResponse.data ?? null,
		locations: locationsResponse.data ?? []
	};
};
