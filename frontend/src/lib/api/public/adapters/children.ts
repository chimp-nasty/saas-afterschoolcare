import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import {
	childResponseSchema,
	childTableResponseSchema,
	type ChildResponse,
	type ChildTableResponse,
	type ListChildrenFilterRequest,
	type CreateChildRequest,
} from '../types/children';


export function createChildrenApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/children/v1`;

	return {
		getById(childId: string) {
			return apiWrapper<ChildResponse>(
				`${baseUrl}/${childId}`,
				{
					method: 'GET',
					fetcher,
					schema: childResponseSchema
				}
			);
		},

		list(
			filters: ListChildrenFilterRequest = {},
			pagination: Pagination = {}
		) {
			const query = buildQueryParams(
				filters,
				pagination
			);

			return apiWrapper<ChildTableResponse[]>(
				`${baseUrl}/${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher,
					schema: z.array(childTableResponseSchema)
				}
			);
		},

		create(
			body: CreateChildRequest
		) {
			return apiWrapper<ChildResponse>(
				`${baseUrl}/`,
				{
					method: 'POST',
					body,
					fetcher,
					schema: childResponseSchema
				}
			);
		}
	};
}