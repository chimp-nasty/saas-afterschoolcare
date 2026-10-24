import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	CreatePickupRequest,
	PickupResponse,
	UpdatePickupRequest
} from '$lib/api/schema';


export function createPickupsApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/pickups/v1`;

	return {
		list() {
			return apiWrapper<PickupResponse[]>(
				`${baseUrl}/`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		getById(pickupId: string) {
			return apiWrapper<PickupResponse>(
				`${baseUrl}/${pickupId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		create(body: CreatePickupRequest) {
			return apiWrapper<PickupResponse>(
				`${baseUrl}/`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		update(
			pickupId: string,
			body: UpdatePickupRequest
		) {
			return apiWrapper<PickupResponse>(
				`${baseUrl}/${pickupId}`,
				{
					method: 'PATCH',
					body,
					fetcher
				}
			);
		},

		deactivate(pickupId: string) {
			return apiWrapper<PickupResponse>(
				`${baseUrl}/${pickupId}/deactivate`,
				{
					method: 'POST',
					fetcher
				}
			);
		}
	};
}
