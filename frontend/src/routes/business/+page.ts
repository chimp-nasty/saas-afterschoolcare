import { createBusinessApi } from '$lib/api/tenancy/adapters/business';

import type { PageLoad } from './$types';

// The setup checklist and centres, and the owner's dashboard for the week
// and centre in the address (?week= weeks from this one, ?week=all for all
// time; ?centre=).
export const load: PageLoad = async ({ depends, fetch, url }) => {
	depends('app:business');

	const asked = url.searchParams.get('week');
	const parsed = Number.parseInt(asked ?? '0', 10);
	const week: number | null = asked === 'all' ? null : Number.isNaN(parsed) ? 0 : parsed;
	const locationId = url.searchParams.get('centre');

	const api = createBusinessApi(fetch);
	const [overview, dashboard] = await Promise.all([api.overview(), api.dashboard(week, locationId)]);

	return {
		overview: overview.data ?? null,
		dashboard: dashboard.data ?? null,
		week,
		locationId
	};
};
