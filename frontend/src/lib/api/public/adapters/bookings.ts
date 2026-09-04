import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	CreateBookingRequest,
	CreateBookingResponse,
	BookingConflictRow,
	BookingResponse,
	BookingTableResponse,
	ListBookingsFilterRequest
} from '../types/bookings';


export function createBookingApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/booking/v1`;

	return {
		create(body: CreateBookingRequest) {
			return apiWrapper<CreateBookingResponse>(
				`${baseUrl}/create`,
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
				`${baseUrl}/read/${bookingId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		list(
			filters: ListBookingsFilterRequest = {}
		) {
			const params = new URLSearchParams();

			for (const status of filters.booking_status ?? []) {
				params.append(
					'booking_status',
					status
				);
			}

			for (const status of filters.payment_status ?? []) {
				params.append(
					'payment_status',
					status
				);
			}

			if (filters.date_from) {
				params.set(
					'date_from',
					filters.date_from
				);
			}

			if (filters.date_to) {
				params.set(
					'date_to',
					filters.date_to
				);
			}

			const query = params.toString();

			return apiWrapper<BookingTableResponse[]>(
				`${baseUrl}/list${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
	};
}