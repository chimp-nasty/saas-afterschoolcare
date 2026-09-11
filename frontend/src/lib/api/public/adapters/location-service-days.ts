import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import {
	locationServiceDayTableResponseSchema,
	type ListLocationServiceDaysFilterRequest,
	type LocationServiceDayTableResponse
} from '../types/location-service-days';


export function createLocationServiceDaysApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/location-service-days/v1`;

	return {
		list(
			filters: ListLocationServiceDaysFilterRequest = {},
		) {
			const query = buildQueryParams(
				filters,
			);

			return apiWrapper<LocationServiceDayTableResponse[]>(
				`${baseUrl}/${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher,
					schema: z.array(locationServiceDayTableResponseSchema)
				}
			);
		}
	};
}