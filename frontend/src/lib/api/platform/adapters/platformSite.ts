import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	ConfirmPlatformUploadRequest,
	PlatformFeatureItem,
	PlatformSiteRequest,
	PlatformSiteResponse,
	SiteUploadResponse,
	StartPlatformUploadRequest
} from '$lib/api/schema';


export type PlatformFileKind = StartPlatformUploadRequest['kind'];

const BASE_URL = `${API_BASE}/platform-site/v1`;

// The platform's logo, icon or a photo (a redirect to the file), with its
// version so a new one isn't hidden by the browser's cache.
export function platformFileUrl(kind: PlatformFileKind, version?: string): string {
	const url = `${BASE_URL}/files/${kind}`;

	return version ? `${url}?v=${encodeURIComponent(version)}` : url;
}

// The platform's landing page and branding (docs/platform-site.md): anyone
// reads it; the platform's admins change it in place on the page.
export function createPlatformSiteApi(
	fetcher?: typeof fetch
) {
	return {
		get() {
			return apiWrapper<PlatformSiteResponse>(`${BASE_URL}/`, { method: 'GET', fetcher });
		},

		update(body: PlatformSiteRequest) {
			return apiWrapper<PlatformSiteResponse>(`${BASE_URL}/`, { method: 'PUT', body, fetcher });
		},

		replaceFeatures(features: PlatformFeatureItem[]) {
			return apiWrapper<PlatformSiteResponse>(`${BASE_URL}/features`, { method: 'PUT', body: { features }, fetcher });
		},

		startUpload(body: StartPlatformUploadRequest) {
			return apiWrapper<SiteUploadResponse>(`${BASE_URL}/uploads`, { method: 'POST', body, fetcher });
		},

		confirmUpload(body: ConfirmPlatformUploadRequest) {
			return apiWrapper<PlatformSiteResponse>(`${BASE_URL}/uploads/confirm`, { method: 'POST', body, fetcher });
		},

		removeFile(kind: PlatformFileKind) {
			return apiWrapper<PlatformSiteResponse>(`${BASE_URL}/files/${kind}`, { method: 'DELETE', fetcher });
		}
	};
}
