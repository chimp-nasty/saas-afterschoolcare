import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type { SetStaffPinRequest, StaffPinStatusResponse } from '$lib/api/schema';


// Your own staff kiosk PIN: set here only, never at the kiosk.
export function createStaffPinApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/staff-pin/v1`;

	return {
		status() {
			return apiWrapper<StaffPinStatusResponse>(
				`${baseUrl}/`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		set(body: SetStaffPinRequest) {
			return apiWrapper<StaffPinStatusResponse>(
				`${baseUrl}/`,
				{
					method: 'PUT',
					body,
					fetcher
				}
			);
		}
	};
}
