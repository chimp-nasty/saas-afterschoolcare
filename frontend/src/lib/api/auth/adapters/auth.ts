import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { LoginRequest, ResetPasswordRequest, ForgotPasswordRequest } from '../types/types';


export const login = async (
	body: LoginRequest,
	fetcher?: typeof fetch
) => {
	return apiWrapper<null>(
		`${PUBLIC_API_URL}/auth/v1/login`,
		{
			method: 'POST',
			body,
			fetcher
		}
	);
};


export const forgotPassword = async (
	body: ForgotPasswordRequest,
	fetcher?: typeof fetch
) => {
	return apiWrapper<null>(
		`${PUBLIC_API_URL}/auth/v1/forgot-password`,
		{
			method: 'POST',
			body,
			fetcher
		}
	);
};


export const resetPassword = async (
	body: ResetPasswordRequest,
	fetcher?: typeof fetch
) => {
	return apiWrapper<null>(
		`${PUBLIC_API_URL}/auth/v1/reset-password`,
		{
			method: 'POST',
			body,
			fetcher
		}
	);
};

