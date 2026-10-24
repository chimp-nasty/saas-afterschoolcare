import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';

import type { LayoutLoad } from './$types';

// Business settings (/business): the business's owner only, logged in here
// (no location) or at one of its centres. Anyone else is sent to the login.
export const load: LayoutLoad = async ({ depends, fetch }) => {
	depends('app:session');
	// Saving Your site invalidates this, so the new colours show at once.
	depends('app:business-site');

	const [response, businessResponse] = await Promise.all([
		createAuthApi(fetch).getSession(),
		createLocationBrandingApi(fetch).getPublicBusiness()
	]);
	const data = response.ok ? response.data : null;

	// The business's colours, like every other page of its site.
	const branding = {
		primaryColor: businessResponse.data?.primary_color ?? null,
		secondaryColor: businessResponse.data?.secondary_color ?? null
	};

	const session =
		data && Object.keys(data.tenant_permissions).length > 0
			? {
					userId: data.user_id,
					email: data.email,
					firstName: data.first_name,
					roles: data.roles,
					tenantPermissions: data.tenant_permissions
				}
			: null;

	return { session, branding };
};
