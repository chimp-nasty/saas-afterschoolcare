import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { AccountResponse, ChangePasswordRequest } from '$lib/api/schema';


// Your own account, for everyone who logs in: read-only details, and
// changing your password.
export function createAccountApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/account/v1`;

	return {
		get() {
			return apiWrapper<AccountResponse>(
				`${baseUrl}/`,
				{
					method: 'GET',
					fetcher
				}
			);
		},

		changePassword(body: ChangePasswordRequest) {
			return apiWrapper<null>(
				`${baseUrl}/password`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		}
	};
}
