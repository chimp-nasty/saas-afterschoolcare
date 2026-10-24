import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';

import type { PageLoad } from './$types';

// Whether the business has terms to link from the sign-up form.
export const load: PageLoad = async ({ fetch }) => {
	const response = await createLocationBrandingApi(fetch).getPublicBusiness();

	return {
		hasTerms: response.data?.has_terms ?? false
	};
};
