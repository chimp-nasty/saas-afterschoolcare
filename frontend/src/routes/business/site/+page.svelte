<!--
    Business settings › Your site: what the business's landing page and
    every centre's pages look like (headline, colours, logo, site icon),
    its questions and answers, and its policies (each upload a new version,
    so what families accepted stays on record).
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import FaqEditor from '$lib/features/business/components/FaqEditor.svelte';
	import HighlightEditor from '$lib/features/business/components/HighlightEditor.svelte';
	import SiteFileUpload from '$lib/features/business/components/SiteFileUpload.svelte';
	import SiteForm from '$lib/features/business/components/SiteForm.svelte';

	import { uploadToStorage } from '$lib/api/storage';
	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import { siteFileUrl, type SiteFileKind } from '$lib/api/tenancy/adapters/location-branding';
	import type { FaqItem, HighlightItem, SiteRequest, StartSiteUploadRequest } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let { data } = $props();

	const businessApi = createBusinessApi();

	const site = $derived(data.site);

	// The types each file may be (checked again by the server, which reads
	// the file itself).
	const ACCEPT: Record<SiteFileKind, StartSiteUploadRequest['content_type'][]> = {
		logo: ['image/png', 'image/jpeg', 'image/webp'],
		icon: ['image/png'],
		privacy: ['application/pdf'],
		terms: ['application/pdf']
	};

	const WRONG_TYPE: Record<SiteFileKind, string> = {
		logo: 'Choose a PNG, JPEG or WebP image.',
		icon: 'Choose a square PNG image.',
		privacy: 'Choose a PDF.',
		terms: 'Choose a PDF.'
	};

	async function refresh() {
		await invalidate('app:business-site');
	}

	async function saveSite(body: SiteRequest) {
		const response = await businessApi.updateSite(body);

		if (response.ok) await refresh();

		return response;
	}

	async function saveFaqs(faqs: FaqItem[]) {
		const response = await businessApi.replaceFaqs(faqs);

		if (response.ok) await refresh();

		return response;
	}

	async function saveHighlights(highlights: HighlightItem[]) {
		const response = await businessApi.replaceHighlights(highlights);

		if (response.ok) await refresh();

		return response;
	}

	// Start the upload, send the file straight to storage, then have the
	// server check it and use it.
	async function upload(kind: SiteFileKind, file: File): Promise<boolean> {
		const contentType = ACCEPT[kind].find((type) => type === file.type);

		if (!contentType) {
			toast.error(WRONG_TYPE[kind]);
			return false;
		}

		const started = await businessApi.startUpload({ kind, content_type: contentType });

		if (!started.ok || !started.data) return false;

		if (!(await uploadToStorage(started.data, file))) {
			toast.error("The file couldn't be uploaded. Check it's small enough and try again.");
			return false;
		}

		const confirmed = await businessApi.confirmUpload({ kind, key: started.data.key });

		if (confirmed.ok) await refresh();

		return confirmed.ok;
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
	<PageHeader title="Your site" description="How your home page and every centre's pages look, your questions and answers, and your policies." />

	{#if site}
		<SectionHeading title="Headline and colours" description="The top of your home page and every centre's page." />

		<SiteForm
			initial={{
				tagline: site.tagline,
				hero_text: site.hero_text,
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
					accept={ACCEPT.logo.join(',')}
					status={site.has_logo ? 'Your logo is showing.' : 'No logo yet: your business name shows instead.'}
					viewHref={site.has_logo ? siteFileUrl('logo') : null}
					onupload={(file) => upload('logo', file)}
					onremove={() => removeImage('logo')}
				/>

				<SiteFileUpload
					title="Site icon"
					description="The small picture in the browser tab and on phone home screens. A square PNG, at least 192 by 192 pixels, up to 1 MB."
					accept={ACCEPT.icon.join(',')}
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
					accept={ACCEPT.privacy.join(',')}
					status={documentStatus('privacy')}
					viewHref={hasDocument('privacy') ? siteFileUrl('privacy') : null}
					onupload={(file) => upload('privacy', file)}
				/>

				<SiteFileUpload
					title="Terms"
					description="A PDF up to 5 MB. Families accept your current terms when they sign up, and which version they accepted is kept."
					accept={ACCEPT.terms.join(',')}
					status={documentStatus('terms')}
					viewHref={hasDocument('terms') ? siteFileUrl('terms') : null}
					onupload={(file) => upload('terms', file)}
				/>
			</div>
		</Card>

		<SectionHeading
			title="Highlights"
			description="Short points under your headline, on your home page and every centre's page. Up to 4."
		/>

		<HighlightEditor initial={site.highlights} onsubmit={saveHighlights} />

		<SectionHeading title="Questions and answers" description="Shown on your home page, in this order. Up to 20." />

		<FaqEditor initial={site.faqs} onsubmit={saveFaqs} />
	{/if}
</Page>
