import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
    FeaturedServiceResponse,
    UpdateLocationServiceConfigRequest,
    LocationServiceSelectionResponse,
    LocationServiceSettingsResponse,
} from '$lib/api/schema';


export function createLocationServicesApi(
    fetcher?: typeof fetch
) {
    const baseUrl =
        `${API_BASE}/location-services/v1`;

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

        // The service the centre's page leads with, and its next session
        // (null when the location offers nothing).
        getFeatured(locationCode: string) {
            return apiWrapper<FeaturedServiceResponse | null>(
                `${baseUrl}/public/${locationCode}/featured`,
                {
                    method: 'GET',
                    fetcher
                }
            );
        },

        // Admins: every service the location has, offered or not.
        settings() {
            return apiWrapper<LocationServiceSettingsResponse[]>(
                `${baseUrl}/settings`,
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
            return apiWrapper<LocationServiceSettingsResponse>(
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
