import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import type {
	operations,
	ChildResponse,
	ChildTableResponse,
	CreateChildRequest,
	UpdateChildRequest
} from '$lib/api/schema';


export type ListChildrenFilter = Omit<
	NonNullable<operations['list_children_api_children_v1__get']['parameters']['query']>,
	keyof Pagination
>;


export function createChildrenApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/children/v1`;

	return {
		getById(childId: string) {
			return apiWrapper<ChildResponse>(
				`${baseUrl}/${childId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		list(
			filters: ListChildrenFilter = {},
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
					fetcher
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
					fetcher
				}
			);
		},

		update(
			childId: string,
			body: UpdateChildRequest
		) {
			return apiWrapper<ChildResponse>(
				`${baseUrl}/${childId}`,
				{
					method: 'PATCH',
					body,
					fetcher
				}
			);
		},

		deactivate(childId: string) {
			return apiWrapper<ChildResponse>(
				`${baseUrl}/${childId}/deactivate`,
				{
					method: 'POST',
					fetcher
				}
			);
		}
	};
}
