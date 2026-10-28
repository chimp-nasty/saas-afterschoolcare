<!--
    Platform › Site: how the platform's own pages look (colours, logo, site
    icon; docs/platform-site.md). The landing page's words, photos and
    feature cards are edited on the page itself, like a business's.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { page } from '$app/state';

	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import SiteFileUpload from '$lib/features/business/components/SiteFileUpload.svelte';
	import SiteForm from '$lib/features/business/components/SiteForm.svelte';

	import { createPlatformSiteApi, platformFileUrl } from '$lib/api/platform/adapters/platformSite';
	import type { SiteRequest, StartPlatformUploadRequest } from '$lib/api/schema';
	import { SITE_FILE_ACCEPT, uploadFile } from '$lib/features/business/siteFiles';

	const platformSiteApi = createPlatformSiteApi();

	// Loaded for every page of the platform's site (routes/+layout.ts).
	const site = $derived(page.data.platformSite);

	async function refresh() {
		await invalidate('app:platform-site');
	}

	async function saveColours(body: SiteRequest) {
		const response = await platformSiteApi.update({
			primary_color: body.primary_color,
			secondary_color: body.secondary_color,
			accent_color: body.accent_color
		});

		if (response.ok) await refresh();

		return response;
	}

	async function upload(kind: 'logo' | 'icon', file: File): Promise<boolean> {
		const accept: StartPlatformUploadRequest['content_type'][] =
			kind === 'icon' ? ['image/png'] : ['image/png', 'image/jpeg', 'image/webp'];

		const ok = await uploadFile(file, {
			accept,
			wrongType: kind === 'icon' ? 'Choose a square PNG image.' : 'Choose a PNG, JPEG or WebP image.',
			start: (contentType) => platformSiteApi.startUpload({ kind, content_type: contentType }),
			confirm: (key) => platformSiteApi.confirmUpload({ kind, key })
		});

		if (ok) await refresh();

		return ok;
	}

	async function remove(kind: 'logo' | 'icon') {
		const response = await platformSiteApi.removeFile(kind);

		if (response.ok) await refresh();
	}
</script>

<Page width="wide">
	<PageHeader title="Site" description="How the platform's own pages look: the home page, contact, registration and this console." />

	<Notice>
		The home page's headline, photos, feature cards and about text are edited on the page itself: open
		<HyperTextLink href="/" inline>the home page</HyperTextLink> on a computer and use the pencil beside each part.
	</Notice>

	{#if site}
		<SectionHeading title="Colours" description="Every page of the platform's site uses them." />

		<SiteForm
			initial={{
				primary_color: site.primary_color,
				secondary_color: site.secondary_color,
				accent_color: site.accent_color
			}}
			onsubmit={saveColours}
		/>

		<Card border>
			<div class="flex flex-col gap-6">
				<SiteFileUpload
					title="Logo"
					description="The wordmark at the top of every page, in place of the name. PNG, JPEG or WebP, up to 1 MB."
					accept={SITE_FILE_ACCEPT.logo.join(',')}
					status={site.has_logo ? 'The logo is showing.' : 'No logo yet: the name shows instead.'}
					viewHref={site.has_logo ? platformFileUrl('logo') : null}
					onupload={(file) => upload('logo', file)}
					onremove={() => remove('logo')}
				/>

				<SiteFileUpload
					title="Site icon"
					description="The small picture in the browser tab and on phone home screens. A square PNG, at least 192 by 192 pixels, up to 1 MB."
					accept={SITE_FILE_ACCEPT.icon.join(',')}
					status={site.has_icon ? 'The icon is showing.' : site.has_logo ? 'No icon yet: the logo is used.' : "No icon yet: the app's is used."}
					viewHref={site.has_icon ? platformFileUrl('icon') : null}
					onupload={(file) => upload('icon', file)}
					onremove={() => remove('icon')}
				/>
			</div>
		</Card>
	{/if}
</Page>
