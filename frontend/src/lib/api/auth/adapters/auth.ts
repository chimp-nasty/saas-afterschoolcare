import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	LoginRequest,
	ResetPasswordRequest,
	ForgotPasswordRequest,
	SessionResponse
} from '$lib/api/schema';


export function createAuthApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/auth/v1`;

	return {
		login(locationCode: string, body: LoginRequest) {
			return apiWrapper<null>(
				`${baseUrl}/login/${locationCode}`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		// Business settings (/business): the owner, with no location.
		businessLogin(body: LoginRequest) {
			return apiWrapper<null>(
				`${baseUrl}/business/login`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		// Another centre of the business, without logging in again (needs a
		// role there): "Manage centre" in Business settings.
		switchLocation(locationCode: string) {
			return apiWrapper<null>(
				`${baseUrl}/switch-location/${locationCode}`,
				{
					method: 'POST',
					fetcher,
					// The page moves on; errors still toast.
					quiet: true
				}
			);
		},

		// Per location, like login: the email comes from that centre.
		forgotPassword(locationCode: string, body: ForgotPasswordRequest) {
			return apiWrapper<null>(
				`${baseUrl}/forgot-password/${locationCode}`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		resetPassword(body: ResetPasswordRequest) {
			return apiWrapper<null>(
				`${baseUrl}/reset-password`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		getSession() {
			return apiWrapper<SessionResponse>(
				`${baseUrl}/session`,
				{
					fetcher
				}
			);
		},

		logout() {
			return apiWrapper<null>(
				`${baseUrl}/logout`,
				{
					method: 'POST',
					fetcher
				}
			);
		}
	};
}
