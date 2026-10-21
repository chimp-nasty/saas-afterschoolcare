import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import type {
	operations,
	CreateServiceDaysRequest,
	CreateServiceDaysResponse,
	LocationServiceDayTableResponse,
	ServiceDayOverviewResponse,
	SetServiceDayCapacityRequest,
	SetServiceDayCapacityResponse,
	UpdateServiceDayRequest
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
		},

		// Admins: a service's days with their places.
		overview(locationServiceId: string, dateFrom: string, dateTo: string) {
			const query = buildQueryParams({
				location_service_id: locationServiceId,
				date_from: dateFrom,
				date_to: dateTo
			});

			return apiWrapper<ServiceDayOverviewResponse[]>(`${baseUrl}/overview?${query}`, {
				method: 'GET',
				fetcher
			});
		},

		// Superadmins: add days (one day is a range of one date).
		create(body: CreateServiceDaysRequest) {
			return apiWrapper<CreateServiceDaysResponse>(`${baseUrl}/`, {
				method: 'POST',
				body,
				fetcher
			});
		},

		// Superadmins: one day's places, or closing or reopening it.
		update(dayId: string, body: UpdateServiceDayRequest) {
			return apiWrapper<ServiceDayOverviewResponse>(`${baseUrl}/${dayId}`, {
				method: 'PATCH',
				body,
				fetcher
			});
		},

		// Superadmins: the same places across a range, all or nothing.
		setCapacity(body: SetServiceDayCapacityRequest) {
			return apiWrapper<SetServiceDayCapacityResponse>(`${baseUrl}/capacity`, {
				method: 'PATCH',
				body,
				fetcher
			});
		},

		// Superadmins: a day that's never been booked.
		remove(dayId: string) {
			return apiWrapper<null>(`${baseUrl}/${dayId}`, {
				method: 'DELETE',
				fetcher
			});
		}
	};
}
