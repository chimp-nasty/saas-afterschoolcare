import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import type {
    UpdateLocationServiceRequest,
    LocationServiceSelectionResponse,
} from "$lib/api/public/types/location-services"


export function createLocationServicesApi(
    fetcher?: typeof fetch
) {
    const baseUrl =
        `${PUBLIC_API_URL}/location-services/v1`;

    return {
        list() {
            return apiWrapper<LocationServiceSelectionResponse[]>(
                `${baseUrl}/list`,
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
                `${baseUrl}/update-price/${location_service_id}`,
                {
                    method: 'POST',
                    body,
                    fetcher
                }
            );
        }
    }
}