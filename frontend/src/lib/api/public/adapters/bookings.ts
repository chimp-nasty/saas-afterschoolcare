import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import {
	createBookingResponseSchema,
	bookingConflictRowSchema,
	bookingResponseSchema,
	bookingTableResponseSchema,
	type CreateBookingRequest,
	type CreateBookingResponse,
	type BookingConflictRow,
	type BookingResponse,
	type BookingTableResponse,
	type ListBookingsFilterRequest
} from '../types/bookings';


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
					fetcher,
					schema: createBookingResponseSchema
				}
			);
		},

		findConflicts(body: CreateBookingRequest) {
			return apiWrapper<BookingConflictRow[]>(
				`${baseUrl}/conflicts`,
				{
					method: 'POST',
					body,
					fetcher,
					schema: z.array(bookingConflictRowSchema)
				}
			);
		},

		getById(bookingId: string) {
			return apiWrapper<BookingResponse>(
				`${baseUrl}/${bookingId}`,
				{
					method: 'GET',
					fetcher,
					schema: bookingResponseSchema
				}
			);
		},

		list(
			filters: ListBookingsFilterRequest = {},
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
					fetcher,
					schema: z.array(bookingTableResponseSchema)
				}
			);
		}
	};
}