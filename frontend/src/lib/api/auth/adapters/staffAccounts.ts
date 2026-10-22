import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	AddStaffRequest,
	AddStaffResponse,
	ChangeStaffRoleRequest,
	RenameStaffRequest,
	StaffAccountResponse
} from '$lib/api/schema';


// Admin › Staff: the location's staff accounts.
export function createStaffAccountsApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${PUBLIC_API_URL}/staff-accounts/v1`;

	return {
		list() {
			return apiWrapper<StaffAccountResponse[]>(`${baseUrl}/`, { method: 'GET', fetcher });
		},

		// New accounts are emailed an invite to set their password.
		add(body: AddStaffRequest) {
			return apiWrapper<AddStaffResponse>(`${baseUrl}/`, { method: 'POST', body, fetcher });
		},

		resendInvite(userId: string) {
			return apiWrapper<StaffAccountResponse>(`${baseUrl}/${userId}/invite`, { method: 'POST', fetcher });
		},

		rename(userId: string, body: RenameStaffRequest) {
			return apiWrapper<StaffAccountResponse>(`${baseUrl}/${userId}`, { method: 'PATCH', body, fetcher });
		},

		// Superadmins: staff <-> admin.
		changeRole(userId: string, body: ChangeStaffRoleRequest) {
			return apiWrapper<StaffAccountResponse>(`${baseUrl}/${userId}/role`, { method: 'PUT', body, fetcher });
		},

		resetPin(userId: string) {
			return apiWrapper<StaffAccountResponse>(`${baseUrl}/${userId}/reset-pin`, { method: 'POST', fetcher });
		},

		// Superadmins: off this location's staff (their account stays).
		remove(userId: string) {
			return apiWrapper<null>(`${baseUrl}/${userId}`, { method: 'DELETE', fetcher });
		}
	};
}
