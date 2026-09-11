import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import {
	sessionResponseSchema,
	type LoginRequest,
	type ResetPasswordRequest,
	type ForgotPasswordRequest,
	type SessionResponse
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
					fetcher,
					schema: z.null()
				}
			);
		},

		forgotPassword(body: ForgotPasswordRequest) {
			return apiWrapper<null>(
				`${baseUrl}/forgot-password`,
				{
					method: 'POST',
					body,
					fetcher,
					schema: z.null()
				}
			);
		},

		resetPassword(body: ResetPasswordRequest) {
			return apiWrapper<null>(
				`${baseUrl}/reset-password`,
				{
					method: 'POST',
					body,
					fetcher,
					schema: z.null()
				}
			);
		},

		getSession() {
			return apiWrapper<SessionResponse>(
				`${baseUrl}/session`,
				{
					fetcher,
					schema: sessionResponseSchema
				}
			);
		},

		logout() {
			return apiWrapper<null>(
				`${baseUrl}/logout`,
				{
					method: 'POST',
					fetcher,
					schema: z.null()
				}
			);
		}
	};
}