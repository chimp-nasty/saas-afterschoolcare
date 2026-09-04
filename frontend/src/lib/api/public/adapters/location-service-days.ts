import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	ListLocationServiceDaysFilterRequest,
	LocationServiceDayTableResponse
} from '../types/location-service-days'


export function createLocationServiceDaysApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/location-service-days/v1`;

	return {
		list(
			filters: ListLocationServiceDaysFilterRequest = {}
		) {
			const params = new URLSearchParams();

			if (filters.date_from) {
				params.set(
					'date_from',
					filters.date_from
				);
			}

			if (filters.date_to) {
				params.set(
					'date_to',
					filters.date_to
				);
			}

			if (
				filters.is_open !== undefined &&
				filters.is_open !== null
			) {
				params.set(
					'is_open',
					String(filters.is_open)
				);
			}

			const query = params.toString();

			return apiWrapper<LocationServiceDayTableResponse[]>(
				`${baseUrl}/list${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
	};
}