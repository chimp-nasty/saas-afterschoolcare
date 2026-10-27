import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
    FeaturedServiceResponse,
    SiteUploadResponse,
    StartPhotoUploadRequest,
    UpdateLocationServiceConfigRequest,
    LocationServiceSelectionResponse,
    LocationServiceSettingsResponse,
} from '$lib/api/schema';


// A program's photo (stage 9b) on the public programs page, with its
// version so a new one isn't hidden by a cached link.
export function programPhotoUrl(locationCode: string, locationServiceId: string, version: string): string {
    return `${API_BASE}/location-services/v1/public/${locationCode}/${locationServiceId}/photo?v=${encodeURIComponent(version)}`;
}


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
        },

        // A program's photo (stage 9b), inline on the programs page: upload
        // (then uploadToStorage, then confirm), taking it off. Its
        // description is saved with updateConfig (photo_alt).
        startPhotoUpload(location_service_id: string, contentType: StartPhotoUploadRequest['content_type']) {
            return apiWrapper<SiteUploadResponse>(`${baseUrl}/${location_service_id}/photo/uploads`, {
                method: 'POST',
                body: { content_type: contentType },
                fetcher,
                quiet: true
            });
        },

        confirmPhotoUpload(location_service_id: string, key: string) {
            return apiWrapper<LocationServiceSettingsResponse>(`${baseUrl}/${location_service_id}/photo/uploads/confirm`, {
                method: 'POST',
                body: { key },
                fetcher
            });
        },

        removePhoto(location_service_id: string) {
            return apiWrapper<LocationServiceSettingsResponse>(`${baseUrl}/${location_service_id}/photo`, {
                method: 'DELETE',
                fetcher
            });
        }
    }
}
