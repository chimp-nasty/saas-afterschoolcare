import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { StripeAccountStatusResponse, StripeOnboardingResponse } from '$lib/api/schema';


// Admin › Payments: the business's Stripe account (Stripe Connect). Admins
// read its status; superadmins connect it and turn payments off or on.
export function createStripeAccountApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/stripe-account/v1`;

	return {
		status() {
			return apiWrapper<StripeAccountStatusResponse>(`${baseUrl}/`, { method: 'GET', fetcher });
		},

		// A one-time link to Stripe's onboarding (it returns to this page).
		onboarding() {
			return apiWrapper<StripeOnboardingResponse>(`${baseUrl}/onboarding`, { method: 'POST', fetcher });
		},

		// "Connect with Stripe": link the business's existing account (OAuth).
		linkExisting() {
			return apiWrapper<StripeOnboardingResponse>(`${baseUrl}/oauth`, { method: 'POST', fetcher });
		},

		refresh() {
			return apiWrapper<StripeAccountStatusResponse>(`${baseUrl}/refresh`, { method: 'POST', fetcher });
		},

		disconnect() {
			return apiWrapper<StripeAccountStatusResponse>(`${baseUrl}/disconnect`, { method: 'POST', fetcher });
		},

		reconnect() {
			return apiWrapper<StripeAccountStatusResponse>(`${baseUrl}/reconnect`, { method: 'POST', fetcher });
		}
	};
}
