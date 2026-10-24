import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type { StripeAccountStatusResponse, StripeOnboardingResponse } from '$lib/api/schema';


// The business's Stripe account (Stripe Connect). A centre's admins read its
// status (Admin › Payments); the owner manages it in Business settings ›
// Payments (tenantStatus and the rest).
export function createStripeAccountApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/stripe-account/v1`;

	return {
		status() {
			return apiWrapper<StripeAccountStatusResponse>(`${baseUrl}/`, { method: 'GET', fetcher });
		},

		// The same, for the owner in Business settings (no location needed).
		tenantStatus() {
			return apiWrapper<StripeAccountStatusResponse>(`${baseUrl}/tenant`, { method: 'GET', fetcher });
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
