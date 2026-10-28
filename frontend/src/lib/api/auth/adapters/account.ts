import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type { AccountResponse, ChangePasswordRequest, DeactivateAccountRequest } from '$lib/api/schema';


// Your own account, for everyone who logs in: read-only details, and
// changing your password. Families also deactivate their account and ask to
// be reactivated (docs/account-deactivation.md).
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
		},

		deactivate(body: DeactivateAccountRequest) {
			return apiWrapper<null>(
				`${baseUrl}/deactivate`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
		},

		requestReactivation() {
			return apiWrapper<null>(
				`${baseUrl}/reactivation-request`,
				{
					method: 'POST',
					fetcher
				}
			);
		}
	};
}
