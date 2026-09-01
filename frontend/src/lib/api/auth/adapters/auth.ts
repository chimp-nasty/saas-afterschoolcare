import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	LoginRequest,
	ResetPasswordRequest,
	ForgotPasswordRequest,
	SessionResponse
} from '../types/types';


export function createAuthApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/auth/v1`;

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

		forgotPassword(body: ForgotPasswordRequest) {
			return apiWrapper<null>(
				`${baseUrl}/forgot-password`,
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