import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { RegistrationRequest } from '$lib/api/auth/types/types';


export function createCustomerApi(
	fetcher?: typeof fetch
) {
    const baseUrl =
		`${PUBLIC_API_URL}/customer/v1`;

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

    }
}