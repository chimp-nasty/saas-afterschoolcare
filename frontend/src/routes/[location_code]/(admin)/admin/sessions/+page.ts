import { createLocationServiceDaysApi } from '$lib/api/public/adapters/location-service-days';
import { createLocationServicesApi } from '$lib/api/public/adapters/location-services';

import type { PageLoad } from './$types';

// "YYYY-MM" this month, at the browser (the admin is at the centre's
// timezone, near enough for picking a month).
function thisMonth(): string {
	const now = new Date();

	return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
}

// The month's first and last dates ("YYYY-MM-DD"), without timezones.
function monthRange(month: string): [string, string] {
	const [year, monthNumber] = month.split('-').map(Number);
	const lastDay = new Date(Date.UTC(year, monthNumber, 0)).getUTCDate();

	return [`${month}-01`, `${month}-${String(lastDay).padStart(2, '0')}`];
}

export const load: PageLoad = async ({
	depends,
	fetch,
	url
}) => {
	depends('app:service-days');

	// The offered services (admins can't see service settings).
	const services = (await createLocationServicesApi(fetch).list()).data ?? [];
	const serviceId = url.searchParams.get('service') ?? services[0]?.id ?? null;
	const month = /^\d{4}-\d{2}$/.test(url.searchParams.get('month') ?? '') ? url.searchParams.get('month')! : thisMonth();
	const [dateFrom, dateTo] = monthRange(month);

	const days = serviceId
		? ((await createLocationServiceDaysApi(fetch).overview(serviceId, dateFrom, dateTo)).data ?? [])
		: [];

	return {
		services,
		serviceId,
		month,
		days
	};
};
