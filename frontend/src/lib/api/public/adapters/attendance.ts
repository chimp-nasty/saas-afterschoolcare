import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { RollResponse, RunSheetResponse } from '$lib/api/schema';


// The website's read-only roll. Attendance is only changed at the kiosks.
export function createAttendanceApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/attendance/v1`;

	return {
		// A day's roll (default today, at the location's date).
		roll(date?: string) {
			const query = buildQueryParams({ date });

			return apiWrapper<RollResponse>(
				`${baseUrl}/roll${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		// The run sheet as the staff kiosk shows it (read-only).
		board(date?: string) {
			const query = buildQueryParams({ date });

			return apiWrapper<RunSheetResponse>(
				`${baseUrl}/board${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
	};
}
