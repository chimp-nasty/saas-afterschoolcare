import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import type {
	operations,
	CreateBookingRequest,
	CreateBookingResponse,
	BookingConflictRow,
	BookingResponse,
	BookingTableResponse
} from '$lib/api/schema';


export type ListBookingsFilter = Omit<
	NonNullable<operations['list_bookings_booking_v1__get']['parameters']['query']>,
	keyof Pagination
>;


export function createBookingApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/booking/v1`;

	return {
		create(body: CreateBookingRequest) {
			return apiWrapper<CreateBookingResponse>(
				`${baseUrl}/`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		findConflicts(body: CreateBookingRequest) {
			return apiWrapper<BookingConflictRow[]>(
				`${baseUrl}/conflicts`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		getById(bookingId: string) {
			return apiWrapper<BookingResponse>(
				`${baseUrl}/${bookingId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		list(
			filters: ListBookingsFilter = {},
			pagination: Pagination = {}
		) {
			const query = buildQueryParams(
				filters,
				pagination
			);

			return apiWrapper<BookingTableResponse[]>(
				`${baseUrl}/${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
	};
}
