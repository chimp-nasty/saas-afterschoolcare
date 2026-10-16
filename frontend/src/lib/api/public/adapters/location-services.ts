import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
    UpdateLocationServiceRequest,
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

        updatePrice(
            location_service_id: string,
            body: UpdateLocationServiceRequest
        ) {
            return apiWrapper<null>(
                `${baseUrl}/${location_service_id}/price`,
                {
                    method: 'PATCH',
                    body,
                    fetcher
                }
            );
        }
    }
}
