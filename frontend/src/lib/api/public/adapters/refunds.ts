import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { RefundResponse } from '$lib/api/schema';


export function createRefundsApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/refunds/v1`;

	return {
		// One booking (one child, one day). Pending until Stripe confirms.
		create(bookingId: string) {
			return apiWrapper<RefundResponse>(
				`${baseUrl}/`,
				{
					method: 'POST',
					body: { booking_id: bookingId },
					fetcher
				}
			);
		}
	};
}
