import { createAttendanceApi } from '$lib/api/public/adapters/attendance';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	url
}) => {
	depends('app:attendance-roll');

	// ?date=YYYY-MM-DD for another day; today (the location's) otherwise.
	// The run sheet is what's shown (as on the staff kiosk); the roll has
	// the pickup lists and phone numbers for the printed sheet.
	const date = url.searchParams.get('date') ?? undefined;
	const api = createAttendanceApi(fetch);
	const [boardResponse, rollResponse] = await Promise.all([api.board(date), api.roll(date)]);

	return {
		board: boardResponse.data,
		roll: rollResponse.data,
		boardError: boardResponse.ok ? null : boardResponse.msg,
		// Today, when no day was asked for.
		today: date ? null : (boardResponse.data?.date ?? null)
	};
};
