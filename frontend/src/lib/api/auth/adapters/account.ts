import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type { AccountResponse, ChangePasswordRequest } from '$lib/api/schema';


// Your own account, for everyone who logs in: read-only details, and
// changing your password.
export function createAccountApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/account/v1`;

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
