import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';
import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';

import type { PageLoad } from './$types';

// The centre's page works before login (docs/public-site.md, section 3):
// its offered services, the one it leads with and its next session, and the
// business's words (hero, highlights, about, FAQs). The location itself
// comes from the layout.
export const load: PageLoad = async ({ depends, fetch, params }) => {
	// Saving a section inline refreshes this, as on the business's pages.
	depends('app:business-site');

	const servicesApi = createLocationServicesApi(fetch);

	const [servicesResponse, featuredResponse, businessResponse] = await Promise.all([
		servicesApi.listPublic(params.location_code),
		servicesApi.getFeatured(params.location_code),
		createLocationBrandingApi(fetch).getPublicBusiness()
	]);

	return {
		services: servicesResponse.data ?? [],
		featured: featuredResponse.data ?? null,
		business: businessResponse.data ?? null
	};
};
