import { error } from '@sveltejs/kit';

import { createAuthApi } from '$lib/api/auth/adapters/auth';
import { createActionsApi } from '$lib/api/public/adapters/actions';
import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';
import { isBusinessOwner } from '$lib/navigation/siteLinks';

import type { LayoutLoad } from './$types';

export const ssr = false;

export const load: LayoutLoad = async ({
	params,
	depends,
	fetch
}) => {
	if (!params.location_code) {
		throw new Error('Location code is required');
	}

	const locationCode = params.location_code;

	// Resolve location
	const brandingApi = createLocationBrandingApi(fetch);

	const locationResponse =
		await brandingApi.getPublicLocation(locationCode);

	if (!locationResponse.ok || !locationResponse.data) {
		error(404, 'Not Found');
	}

	// Resolve session
	depends('app:session');

	const authApi = createAuthApi(fetch);

	const sessionResponse =
		await authApi.getSession();

	const loggedIn =
		sessionResponse.ok && sessionResponse.data
			? {
					userId: sessionResponse.data.user_id,
					email: sessionResponse.data.email,
					firstName: sessionResponse.data.first_name,
					roles: sessionResponse.data.roles,
					locationCode: sessionResponse.data.location_code,
					locationName: sessionResponse.data.location_name,
					tenantPermissions: sessionResponse.data.tenant_permissions
				}
			: null;

	// Logins are per location: a session only counts at its own location.
	// Elsewhere the user is treated as logged out (no nav, protected pages
	// go to the landing page), which shows where they're logged in instead.
	// A Business settings login has no location, so it counts nowhere here.
	const session =
		loggedIn && loggedIn.locationCode === locationCode
			? loggedIn
			: null;

	const signedInElsewhere =
		loggedIn && !session && loggedIn.locationCode
			? {
					locationCode: loggedIn.locationCode,
					locationName: loggedIn.locationName
				}
			: null;

	// Resolve action count
	depends('app:actions-count');

	let uncitedActionCount = 0;

	// Actions are messages to families; staff and admins don't get them.
	if (session?.roles.includes('customer')) {
		const actionsApi = createActionsApi(fetch);

		const actionCountResponse =
			await actionsApi.countUncited();

		uncitedActionCount =
			actionCountResponse.data ?? 0;
	}

	return {
		locationCode,
		location: locationResponse.data,
		session,
		signedInElsewhere,
		uncitedActionCount,
		// The business's owner, logged in anywhere on this site (here, another
		// centre or Business settings): their permissions are the business's,
		// not a centre's. For the Business link and editing the pages' words
		// inline (docs/public-site.md); the API decides what they may do.
		isOwner: isBusinessOwner(loggedIn?.tenantPermissions)
	};
};