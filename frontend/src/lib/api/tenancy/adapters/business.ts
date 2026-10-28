import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	AddDomainRequest,
	BusinessLocationRequest,
	BusinessLocationResponse,
	BusinessOverviewResponse,
	OwnerDashboardResponse,
	BusinessSettingsRequest,
	BusinessSettingsResponse,
	ConfirmSiteUploadRequest,
	DomainResponse,
	DomainsResponse,
	FaqItem,
	HighlightItem,
	SiteRequest,
	SiteResponse,
	SiteUploadResponse,
	PhotoResponse,
	StartPhotoUploadRequest,
	StartSiteUploadRequest
} from '$lib/api/schema';


// Business settings (/business): the whole business, run by its owner
// (tenant permissions; docs/tenant-administration.md).
export function createBusinessApi(
	fetcher?: typeof fetch
) {
	const baseUrl =
		`${API_BASE}/business/v1`;

	return {
		overview() {
			return apiWrapper<BusinessOverviewResponse>(`${baseUrl}/overview`, { method: 'GET', fetcher });
		},

		// The owner's dashboard (docs/owner-dashboard.md): a week (weeks from
		// this one: -1 last week), or all time (null); every centre, or one.
		dashboard(week: number | null, locationId: string | null) {
			const query = new URLSearchParams(week === null ? { all_time: 'true' } : { week: String(week) });
			if (locationId) query.set('location_id', locationId);

			return apiWrapper<OwnerDashboardResponse>(`${baseUrl}/dashboard?${query}`, { method: 'GET', fetcher });
		},

		settings() {
			return apiWrapper<BusinessSettingsResponse>(`${baseUrl}/settings`, { method: 'GET', fetcher });
		},

		updateSettings(body: BusinessSettingsRequest) {
			return apiWrapper<BusinessSettingsResponse>(`${baseUrl}/settings`, { method: 'PUT', body, fetcher });
		},

		locations() {
			return apiWrapper<BusinessLocationResponse[]>(`${baseUrl}/locations`, { method: 'GET', fetcher });
		},

		createLocation(body: BusinessLocationRequest) {
			return apiWrapper<BusinessLocationResponse>(`${baseUrl}/locations`, { method: 'POST', body, fetcher });
		},

		updateLocation(locationId: string, body: BusinessLocationRequest) {
			return apiWrapper<BusinessLocationResponse>(`${baseUrl}/locations/${locationId}`, { method: 'PUT', body, fetcher });
		},

		// A centre's photo (stage 9b), inline on its page: upload (then
		// uploadToStorage, then confirm), its description, taking it off.
		startCentrePhotoUpload(locationId: string, contentType: StartPhotoUploadRequest['content_type']) {
			return apiWrapper<SiteUploadResponse>(`${baseUrl}/locations/${locationId}/photo/uploads`, {
				method: 'POST',
				body: { content_type: contentType },
				fetcher,
				quiet: true
			});
		},

		confirmCentrePhotoUpload(locationId: string, key: string) {
			return apiWrapper<PhotoResponse | null>(`${baseUrl}/locations/${locationId}/photo/uploads/confirm`, {
				method: 'POST',
				body: { key },
				fetcher
			});
		},

		updateCentrePhotoAlt(locationId: string, alt: string | null) {
			return apiWrapper<PhotoResponse | null>(`${baseUrl}/locations/${locationId}/photo`, {
				method: 'PATCH',
				body: { alt },
				fetcher
			});
		},

		removeCentrePhoto(locationId: string) {
			return apiWrapper<PhotoResponse | null>(`${baseUrl}/locations/${locationId}/photo`, {
				method: 'DELETE',
				fetcher
			});
		},

		// Your site (stage 5): headline, colours, logo and icon, FAQs, policies.
		site() {
			return apiWrapper<SiteResponse>(`${baseUrl}/site`, { method: 'GET', fetcher });
		},

		updateSite(body: SiteRequest) {
			return apiWrapper<SiteResponse>(`${baseUrl}/site`, { method: 'PUT', body, fetcher });
		},

		replaceFaqs(faqs: FaqItem[]) {
			return apiWrapper<SiteResponse>(`${baseUrl}/site/faqs`, { method: 'PUT', body: { faqs }, fetcher });
		},

		replaceHighlights(highlights: HighlightItem[]) {
			return apiWrapper<SiteResponse>(`${baseUrl}/site/highlights`, {
				method: 'PUT',
				body: { highlights },
				fetcher
			});
		},

		// A signed upload straight to storage (then uploadToStorage, then confirm).
		startUpload(body: StartSiteUploadRequest) {
			return apiWrapper<SiteUploadResponse>(`${baseUrl}/site/uploads`, { method: 'POST', body, fetcher, quiet: true });
		},

		confirmUpload(body: ConfirmSiteUploadRequest) {
			return apiWrapper<SiteResponse>(`${baseUrl}/site/uploads/confirm`, { method: 'POST', body, fetcher });
		},

		removeImage(kind: 'logo' | 'icon' | 'hero_photo' | 'about_photo') {
			return apiWrapper<SiteResponse>(`${baseUrl}/site/${kind}`, { method: 'DELETE', fetcher });
		},

		// Domains (stage 6): the business's own domains and their DNS records.
		domains() {
			return apiWrapper<DomainsResponse>(`${baseUrl}/domains`, { method: 'GET', fetcher });
		},

		addDomain(body: AddDomainRequest) {
			return apiWrapper<DomainResponse>(`${baseUrl}/domains`, { method: 'POST', body, fetcher });
		},

		checkDomains() {
			return apiWrapper<DomainsResponse>(`${baseUrl}/domains/check`, { method: 'POST', fetcher });
		},

		removeDomain(domainId: string) {
			return apiWrapper<DomainsResponse>(`${baseUrl}/domains/${domainId}`, { method: 'DELETE', fetcher });
		}
	};
}
