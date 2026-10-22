import { error } from '@sveltejs/kit';

import { createFamiliesApi } from '$lib/api/public/adapters/families';

import type { PageLoad } from './$types';

export const load: PageLoad = async ({
	depends,
	fetch,
	params,
	url
}) => {
	depends('app:family');

	const api = createFamiliesApi(fetch);
	const userId = params.user_id;
	// Each list's own range (defaults are the server's).
	const bookingsFrom = url.searchParams.get('bookings_from');
	const bookingsTo = url.searchParams.get('bookings_to');
	const attendanceFrom = url.searchParams.get('attendance_from');
	const attendanceTo = url.searchParams.get('attendance_to');

	const [family, bookings, attendance, payments, notes, messages] = await Promise.all([
		api.get(userId),
		api.bookings(userId, bookingsFrom, bookingsTo),
		api.attendance(userId, attendanceFrom, attendanceTo),
		api.payments(userId),
		api.notes(userId),
		api.messages(userId)
	]);

	if (!family.ok || !family.data) {
		error(404, 'Family not found');
	}

	return {
		family: family.data,
		bookings: bookings.data ?? [],
		attendance: attendance.data ?? [],
		payments: payments.data ?? [],
		notes: notes.data ?? [],
		messages: messages.data ?? [],
		ranges: { bookingsFrom, bookingsTo, attendanceFrom, attendanceTo }
	};
};
