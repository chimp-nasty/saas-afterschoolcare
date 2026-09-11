import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type { RegistrationRequest } from '$lib/api/auth/types/types';

import {
	customerProfileResponseSchema,
	type UpdateCustomerProfileRequest,
	type CustomerProfileResponse,
} from '../types/customer';


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
					fetcher,
					schema: z.null()
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
					fetcher,
					schema: customerProfileResponseSchema
				}
			);
		},

		getProfile() {
			return apiWrapper<CustomerProfileResponse>(
				`${baseUrl}/profile`, 
				{
					method: 'GET',
					fetcher,
					schema: customerProfileResponseSchema
				}
			);
		}
    }
}