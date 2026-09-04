import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	ChildResponse,
	ChildTableResponse,
	ListChildrenFilterRequest
} from '../types/children';


export function createChildrenApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/children/v1`;

	return {
		getById(childId: string) {
			return apiWrapper<ChildResponse>(
				`${baseUrl}/read/${childId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		list(
			filters: ListChildrenFilterRequest = {}
		) {
			const params = new URLSearchParams();

			if (filters.is_active !== undefined && filters.is_active !== null) {
				params.set(
					'is_active',
					String(filters.is_active)
				);
			}

			for (const status of filters.review_status ?? []) {
				params.append(
					'review_status',
					status
				);
			}

			const query = params.toString();

			return apiWrapper<ChildTableResponse[]>(
				`${baseUrl}/list${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
	};
}