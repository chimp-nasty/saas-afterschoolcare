import { z } from 'zod';
import { PUBLIC_API_URL } from '$env/static/public';

import { apiWrapper } from '$lib/api/wrapper';

import {
    locationServiceSelectionResponseSchema,
    type UpdateLocationServiceRequest,
    type LocationServiceSelectionResponse,
} from "$lib/api/public/types/location-services"


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
                    fetcher,
                    schema: z.array(locationServiceSelectionResponseSchema)
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
                    fetcher,
                    schema: z.null()
                }
            );
        }
    }
}