import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	CreatedInviteResponse,
	CreateInviteRequest,
	InviteDetailsResponse,
	InviteResponse,
	LoginRequest,
	PlatformSessionResponse,
	PlatformTenantResponse,
	RegisteredTenantResponse,
	RegisterTenantRequest
} from '$lib/api/schema';


// The platform's site (the bare base domain): its admins, and businesses
// registering with an invite (docs/tenant-administration.md, stage 4).
export function createPlatformApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/platform/v1`;

	return {
		login(body: LoginRequest) {
			return apiWrapper<null>(`${baseUrl}/login`, { method: 'POST', body, fetcher });
		},

		logout() {
			return apiWrapper<null>(`${baseUrl}/logout`, { method: 'POST', fetcher });
		},

		getSession() {
			return apiWrapper<PlatformSessionResponse>(`${baseUrl}/session`, { method: 'GET', fetcher });
		},

		tenants() {
			return apiWrapper<PlatformTenantResponse[]>(`${baseUrl}/tenants`, { method: 'GET', fetcher });
		},

		setTenantActive(tenantId: string, isActive: boolean) {
			return apiWrapper<null>(`${baseUrl}/tenants/${tenantId}/active`, {
				method: 'PUT',
				body: { is_active: isActive },
				fetcher
			});
		},

		invites() {
			return apiWrapper<InviteResponse[]>(`${baseUrl}/invites`, { method: 'GET', fetcher });
		},

		createInvite(body: CreateInviteRequest) {
			return apiWrapper<CreatedInviteResponse>(`${baseUrl}/invites`, { method: 'POST', body, fetcher });
		},

		revokeInvite(inviteId: string) {
			return apiWrapper<null>(`${baseUrl}/invites/${inviteId}`, { method: 'DELETE', fetcher });
		}
	};
}


export function createRegistrationApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/registration/v1`;

	return {
		invite(token: string) {
			return apiWrapper<InviteDetailsResponse>(`${baseUrl}/invites/${encodeURIComponent(token)}`, { method: 'GET', fetcher });
		},

		register(body: RegisterTenantRequest) {
			return apiWrapper<RegisteredTenantResponse>(`${baseUrl}/register`, { method: 'POST', body, fetcher });
		}
	};
}
