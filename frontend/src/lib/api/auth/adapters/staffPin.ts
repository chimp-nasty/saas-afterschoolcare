import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { SetStaffPinRequest, StaffPinStatusResponse } from '$lib/api/schema';


// Your own staff kiosk PIN: set here only, never at the kiosk.
export function createStaffPinApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/staff-pin/v1`;

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
