import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	RegistrationRequest,
	UpdateCustomerProfileRequest,
	CustomerProfileResponse
} from '$lib/api/schema';


export function createCustomerApi(
	fetcher?: typeof fetch
) {
    const baseUrl =
		`${API_BASE}/customer/v1`;

    return {
        onboard(locationCode: string, body: RegistrationRequest) {
            return apiWrapper<null>(
				`${baseUrl}/onboard/${locationCode}`,
				{
					method: 'POST',
					body,
					fetcher
				}
			);
        },

		updateProfile(
			body: UpdateCustomerProfileRequest
		) {
			return apiWrapper<CustomerProfileResponse>(
				`${baseUrl}/profile`,
				{
					method: 'PATCH',
					body,
					fetcher
				}
			);
		},

		getProfile() {
			return apiWrapper<CustomerProfileResponse>(
				`${baseUrl}/profile`,
				{
					method: 'GET',
					fetcher
				}
			);
		}
    }
}
