import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';
import { buildQueryParams } from '$lib/api/param';

import type { Pagination } from '$lib/types/pagination';

import type {
	operations,
	CreateBookingRequest,
	CreateBookingResponse,
	BookingConflictRow,
	BookingResponse,
	BookingTableResponse,
	BookingGroupResponse,
	BookingGroupSummaryResponse,
	CheckoutStatusResponse,
	CheckoutUrlResponse
} from '$lib/api/schema';


export type ListBookingsFilter = Omit<
	NonNullable<operations['list_bookings_api_booking_v1__get']['parameters']['query']>,
	keyof Pagination
>;

export type ListBookingGroupsFilter = Omit<
	NonNullable<operations['list_booking_groups_api_booking_v1_groups_get']['parameters']['query']>,
	keyof Pagination
>;


export function createBookingApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/booking/v1`;

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

		listGroups(
			filters: ListBookingGroupsFilter = {},
			pagination: Pagination = {}
		) {
			const query = buildQueryParams(
				filters,
				pagination
			);

			return apiWrapper<BookingGroupSummaryResponse[]>(
				`${baseUrl}/groups${query ? `?${query}` : ''}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		getGroup(bookingGroupId: string) {
			return apiWrapper<BookingGroupResponse>(
				`${baseUrl}/groups/${bookingGroupId}`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		createGroupCheckout(bookingGroupId: string) {
			return apiWrapper<CheckoutUrlResponse>(
				`${baseUrl}/groups/${bookingGroupId}/checkout`,
				{
					method: 'POST',
					fetcher
				}
			);
		},

		// One paid booking, without a refund: after the refund cutoff,
		// until its session starts. It stays paid, so it can be put back.
		cancel(bookingId: string) {
			return apiWrapper<null>(`${baseUrl}/${bookingId}/cancel`, { method: 'POST', fetcher });
		},

		// A booking cancelled without a refund, back again if there's a place.
		reinstate(bookingId: string) {
			return apiWrapper<null>(`${baseUrl}/${bookingId}/reinstate`, { method: 'POST', fetcher });
		},

		cancelGroup(bookingGroupId: string) {
			return apiWrapper<null>(
				`${baseUrl}/groups/${bookingGroupId}/cancel`,
				{
					method: 'POST',
					fetcher
				}
			);
		},

		getCheckoutStatus(checkoutSessionId: string) {
			return apiWrapper<CheckoutStatusResponse>(
				`${baseUrl}/checkout/${checkoutSessionId}`,
				{
					method: 'GET',
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
