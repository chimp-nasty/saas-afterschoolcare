import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import type {
	operations,
	LocationServiceDayTableResponse
} from '$lib/api/schema';


export type ListLocationServiceDaysFilter = Omit<
	NonNullable<operations['list_location_service_days_location_service_days_v1__get']['parameters']['query']>,
	keyof Pagination
>;


export function createLocationServiceDaysApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/location-service-days/v1`;

	return {
		list(
			filters: ListLocationServiceDaysFilter = {},
		) {
			const query = buildQueryParams(
				filters,
			);

			return apiWrapper<LocationServiceDayTableResponse[]>(
				`${baseUrl}/${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
	};
}
