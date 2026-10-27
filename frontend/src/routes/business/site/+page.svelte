<!--
    Business settings › Your site: how the business's pages look (colours,
    logo, site icon) and its policies (each upload a new version, so what
    families accepted stays on record). The pages' words (headline,
    highlights, about, questions) are edited on the pages themselves
    (docs/public-site.md, section 6).
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';

	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import SiteFileUpload from '$lib/features/business/components/SiteFileUpload.svelte';
	import SiteForm from '$lib/features/business/components/SiteForm.svelte';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import { SITE_FILE_ACCEPT, uploadSiteFile } from '$lib/features/business/siteFiles';
	import { siteFileUrl, type SiteFileKind } from '$lib/api/tenancy/adapters/location-branding';
	import type { SiteRequest } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let { data } = $props();

	const businessApi = createBusinessApi();

	const site = $derived(data.site);

	async function refresh() {
		await invalidate('app:business-site');
	}

	async function saveSite(body: SiteRequest) {
		const response = await businessApi.updateSite(body);

		if (response.ok) await refresh();

		return response;
	}


	async function upload(kind: SiteFileKind, file: File): Promise<boolean> {
		const ok = await uploadSiteFile(businessApi, kind, file);

		if (ok) await refresh();

		return ok;
	}

	async function removeImage(kind: 'logo' | 'icon') {
		const response = await businessApi.removeImage(kind);

		if (response.ok) await refresh();
	}

	function documentStatus(kind: 'privacy' | 'terms') {
		const current = site?.documents.find((document) => document.kind === kind);

		return current ? `Current version uploaded ${formatTimestamp(current.uploaded_at)}.` : 'None uploaded yet.';
	}

	function hasDocument(kind: 'privacy' | 'terms') {
		return Boolean(site?.documents.some((document) => document.kind === kind));
	}
</script>

<Page width="wide">
	<PageHeader title="Your site" description="How your home page and every centre's pages look, and your policies." />

	<Notice>
		Your headline, highlights, about text and questions are edited on your site itself: open
		<HyperTextLink href="/" inline>your home page</HyperTextLink> on a computer and use the pencil beside each part.
	</Notice>

	{#if site}
		<SectionHeading title="Colours" description="Every page of your site uses them." />

		<SiteForm
			initial={{
				primary_color: site.primary_color,
				secondary_color: site.secondary_color,
				accent_color: site.accent_color
			}}
			onsubmit={saveSite}
		/>

		<Card border>
			<div class="flex flex-col gap-6">
				<SiteFileUpload
					title="Logo"
					description="Shown at the top of your pages. PNG, JPEG or WebP, up to 1 MB."
					accept={SITE_FILE_ACCEPT.logo.join(',')}
					status={site.has_logo ? 'Your logo is showing.' : 'No logo yet: your business name shows instead.'}
					viewHref={site.has_logo ? siteFileUrl('logo') : null}
					onupload={(file) => upload('logo', file)}
					onremove={() => removeImage('logo')}
				/>

				<SiteFileUpload
					title="Site icon"
					description="The small picture in the browser tab and on phone home screens. A square PNG, at least 192 by 192 pixels, up to 1 MB."
					accept={SITE_FILE_ACCEPT.icon.join(',')}
					status={site.has_icon ? 'Your icon is showing.' : site.has_logo ? 'No icon yet: your logo is used.' : 'No icon yet.'}
					viewHref={site.has_icon ? siteFileUrl('icon') : null}
					onupload={(file) => upload('icon', file)}
					onremove={() => removeImage('icon')}
				/>
			</div>
		</Card>

		<Card border>
			<div class="flex flex-col gap-6">
				<SiteFileUpload
					title="Privacy policy"
					description="A PDF up to 5 MB, linked at the foot of your home page. Each upload replaces it on your site; earlier versions are kept."
					accept={SITE_FILE_ACCEPT.privacy.join(',')}
					status={documentStatus('privacy')}
					viewHref={hasDocument('privacy') ? siteFileUrl('privacy') : null}
					onupload={(file) => upload('privacy', file)}
				/>

				<SiteFileUpload
					title="Terms"
					description="A PDF up to 5 MB. Families accept your current terms when they sign up, and which version they accepted is kept."
					accept={SITE_FILE_ACCEPT.terms.join(',')}
					status={documentStatus('terms')}
					viewHref={hasDocument('terms') ? siteFileUrl('terms') : null}
					onupload={(file) => upload('terms', file)}
				/>
			</div>
		</Card>
	{/if}
</Page>
