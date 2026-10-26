import { API_BASE } from '$lib/api/base';

import { apiWrapper } from '$lib/api/wrapper';

import type {
	AddDomainRequest,
	BusinessLocationRequest,
	BusinessLocationResponse,
	BusinessOverviewResponse,
	BusinessSettingsRequest,
	BusinessSettingsResponse,
	ConfirmSiteUploadRequest,
	DomainResponse,
	DomainsResponse,
	FaqItem,
	SiteRequest,
	SiteResponse,
	SiteUploadResponse,
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

		// A signed upload straight to storage (then uploadToStorage, then confirm).
		startUpload(body: StartSiteUploadRequest) {
			return apiWrapper<SiteUploadResponse>(`${baseUrl}/site/uploads`, { method: 'POST', body, fetcher, quiet: true });
		},

		confirmUpload(body: ConfirmSiteUploadRequest) {
			return apiWrapper<SiteResponse>(`${baseUrl}/site/uploads/confirm`, { method: 'POST', body, fetcher });
		},

		removeImage(kind: 'logo' | 'icon') {
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
