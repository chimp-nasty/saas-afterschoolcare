import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
    UpdateLocationServiceConfigRequest,
    LocationServiceSelectionResponse,
} from '$lib/api/schema';


export function createLocationServicesApi(
    fetcher?: typeof fetch
) {
    const baseUrl =
        `${PUBLIC_API_URL}/location-services/v1`;

    return {
        list() {
            return apiWrapper<LocationServiceSelectionResponse[]>(
                `${baseUrl}/`,
                {
                    method: 'GET',
                    fetcher
                }
            );
        },

        // Before login (the landing page): the location's offered services.
        listPublic(locationCode: string) {
            return apiWrapper<LocationServiceSelectionResponse[]>(
                `${baseUrl}/public/${locationCode}`,
                {
                    method: 'GET',
                    fetcher
                }
            );
        },

        // Admins: price, times, description, policies.
        updateConfig(
            location_service_id: string,
            body: UpdateLocationServiceConfigRequest
        ) {
            return apiWrapper<LocationServiceSelectionResponse>(
                `${baseUrl}/${location_service_id}/config`,
                {
                    method: 'PATCH',
                    body,
                    fetcher
                }
            );
        }
    }
}
