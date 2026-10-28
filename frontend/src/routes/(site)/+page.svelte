<!--
    The business's landing page ("/", docs/public-site.md): its headline, its
    centres (each a way in; all of them on /locations), a taste of its about
    text (the rest on /about) and its FAQs. A section with nothing to show is
    left out. Its owner edits the words where they are, on desktop
    (EditableSection; section 6). The header and footer are the layout's.
    On the platform's own site, Session Pilot's landing page instead.
-->
<script lang="ts">
	import { goto, invalidate } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import AboutForm from '$lib/features/business/components/AboutForm.svelte';
	import FaqEditor from '$lib/features/business/components/FaqEditor.svelte';
	import FaqList from '$lib/features/business/components/FaqList.svelte';
	import HeroForm from '$lib/features/business/components/HeroForm.svelte';
	import HighlightEditor from '$lib/features/business/components/HighlightEditor.svelte';
	import Highlights from '$lib/features/business/components/Highlights.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';
	import PlatformLanding from '$lib/features/platform/components/PlatformLanding.svelte';
	import EditablePhoto from '$lib/features/business/components/EditablePhoto.svelte';
	import { uploadPhoto as uploadPhotoFile, uploadSiteFile } from '$lib/features/business/siteFiles';

	import { createPlatformSiteApi } from '$lib/api/platform/adapters/platformSite';
	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { ApiResponse } from '$lib/api/wrapper';

	let { data } = $props();

	const businessApi = createBusinessApi();

	// At most this many centres here; the rest are on /locations.
	const CENTRES_SHOWN = 3;
	// About this long here, then "More about us".
	const ABOUT_TASTE = 280;

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Choose your centre');
	const canEdit = $derived(data.isOwner);

	const highlights = $derived(business?.highlights ?? []);
	const faqs = $derived(business?.faqs ?? []);

	const aboutTaste = $derived.by(() => {
		const about = business?.about ?? '';

		return about.length > ABOUT_TASTE ? `${about.slice(0, ABOUT_TASTE).trimEnd()}…` : about;
	});

	// Save a section, then show the page's new content in its place.
	async function save<T>(response: Promise<ApiResponse<T>>, done: () => void) {
		const result = await response;

		if (result.ok) {
			await invalidate('app:business-site');
			done();
		}

		return result;
	}

	type PhotoKind = 'hero_photo' | 'about_photo';

	// The photos (stage 9): an upload or removal takes effect at once.
	async function uploadPhoto(kind: PhotoKind, file: File) {
		const ok = await uploadSiteFile(businessApi, kind, file);

		if (ok) await invalidate('app:business-site');

		return ok;
	}

	async function removePhoto(kind: PhotoKind) {
		const response = await businessApi.removeImage(kind);

		if (response.ok) await invalidate('app:business-site');
	}

	async function savePhotoAlt(kind: PhotoKind, alt: string | null) {
		const response = await businessApi.updateSite({ [`${kind}_alt`]: alt });

		if (response.ok) await invalidate('app:business-site');

		return response;
	}

	// The platform's own landing page (docs/platform-site.md), edited in
	// place by its admins: the same as a business's sections.
	const platformSiteApi = createPlatformSiteApi();

	async function savePlatform<T>(response: Promise<ApiResponse<T>>, done: () => void) {
		const result = await response;

		if (result.ok) {
			await invalidate('app:platform-site');
			done();
		}

		return result;
	}

	async function uploadPlatformPhoto(kind: PhotoKind, file: File) {
		const ok = await uploadPhotoFile(
			file,
			(contentType) => platformSiteApi.startUpload({ kind, content_type: contentType }),
			(key) => platformSiteApi.confirmUpload({ kind, key })
		);

		if (ok) await invalidate('app:platform-site');

		return ok;
	}

	async function removePlatformPhoto(kind: PhotoKind) {
		const response = await platformSiteApi.removeFile(kind);

		if (response.ok) await invalidate('app:platform-site');
	}

	// Room for a photo when there is one, or its owner may add one.
	const heroPhotoColumn = $derived(Boolean(business?.hero_photo) || canEdit);
	const aboutPhotoColumn = $derived(Boolean(business?.about_photo) || canEdit);
</script>

{#if data.platform}
	<!-- The platform's own site: Session Pilot's landing page
	     (docs/platform-site.md). -->
	<PlatformLanding
		site={data.platformSite}
		canEdit={data.isPlatformAdmin}
		onsave={(body, done) => savePlatform(platformSiteApi.update(body), done)}
		onsavefeatures={(features, done) => savePlatform(platformSiteApi.replaceFeatures(features), done)}
		onupload={uploadPlatformPhoto}
		onremove={removePlatformPhoto}
	/>
{:else}
	<!-- The hero: the business's headline and paragraph beside its photo,
	     then its highlights. -->
	<SiteSection>
		<div class={['grid gap-10 lg:items-center', heroPhotoColumn && 'lg:grid-cols-2']}>
			<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
				<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

				<EditableSection {canEdit} label="the headline">
					<div class="flex flex-col gap-5 pr-14">
						{#if business?.tagline}
							<p class="label-text">{name}</p>
						{/if}

						<h1 class="display-text">{business?.tagline ?? name}</h1>

						<p class="text-base text-(--text-muted) md:text-lg">
							{business?.hero_text ?? 'Choose your centre to see its services and book.'}
						</p>
					</div>

					{#snippet editor(done)}
						<HeroForm
							initial={{
								tagline: business?.tagline ?? null,
								hero_text: business?.hero_text ?? null
							}}
							onsubmit={(body) => save(businessApi.updateSite(body), done)}
							oncancel={done}
						/>
					{/snippet}
				</EditableSection>

				{#if data.locations.length > 0}
					<ActionBar start>
						{#if data.locations.length === 1}
							<Button onclick={() => goto(`/${data.locations[0].location_code}`)}>
								Go to {data.locations[0].location_name}
							</Button>
						{:else}
							<Button onclick={() => goto('/locations')}>Find your centre</Button>
						{/if}
					</ActionBar>
				{/if}
			</div>

			{#if heroPhotoColumn}
				<div class={[!business?.hero_photo && 'hidden md:block']}>
					<EditablePhoto
						{canEdit}
						src={business?.hero_photo ? siteFileUrl('hero_photo', business.hero_photo.version) : null}
						photo={business?.hero_photo ?? null}
						emptyPrompt="Add a photo beside your headline"
						shape="wave"
						onupload={(file) => uploadPhoto('hero_photo', file)}
						onremove={() => removePhoto('hero_photo')}
						onsavealt={(alt) => savePhotoAlt('hero_photo', alt)}
					/>
				</div>
			{/if}
		</div>

		{#if highlights.length > 0 || canEdit}
			<div
				class={['border-t border-(--border) pt-8', highlights.length === 0 && 'hidden md:block']}
			>
				<EditableSection
					{canEdit}
					label="the highlights"
					isEmpty={highlights.length === 0}
					emptyPrompt="Add highlights under your headline"
				>
					<Highlights {highlights} />

					{#snippet editor(done)}
						<HighlightEditor
							initial={highlights}
							onsubmit={(items) => save(businessApi.replaceHighlights(items), done)}
							oncancel={done}
						/>
					{/snippet}
				</EditableSection>
			</div>
		{/if}
	</SiteSection>

	<SiteSection tone="muted">
		<SiteHeading title="Our centres" />

		{#if data.locations.length > 0}
			<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
				{#each data.locations.slice(0, CENTRES_SHOWN) as location (location.location_code)}
					<CentreCard {location} href={`/${location.location_code}`} />
				{/each}
			</div>

			<div>
				<HyperTextLink href="/locations">
					{data.locations.length > CENTRES_SHOWN
						? `See all ${data.locations.length} locations`
						: 'Services and times at each centre'}
				</HyperTextLink>
			</div>
		{:else}
			<Card border>
				<EmptyState
					message="We couldn't find any centres here. Use the link your centre gave you."
				/>
			</Card>
		{/if}
	</SiteSection>

	{#if business?.about || canEdit}
		<SiteSection desktopOnly={!business?.about}>
			<div class={['grid gap-10 lg:items-center', aboutPhotoColumn && 'lg:grid-cols-2']}>
				<EditableSection
					{canEdit}
					label="your about text"
					isEmpty={!business?.about}
					emptyPrompt="Add a few words about your business"
				>
					<div class="flex flex-col gap-6">
						<SiteHeading title={`About ${name}`} />

						<p class="max-w-3xl text-base whitespace-pre-line text-(--text) md:text-lg">
							{aboutTaste}
						</p>

						<div>
							<HyperTextLink href="/about">More about us</HyperTextLink>
						</div>
					</div>

					{#snippet editor(done)}
						<AboutForm
							initial={business?.about ?? null}
							onsubmit={(body) => save(businessApi.updateSite(body), done)}
							oncancel={done}
						/>
					{/snippet}
				</EditableSection>

				{#if aboutPhotoColumn}
					<div class={[!business?.about_photo && 'hidden md:block']}>
						<EditablePhoto
							{canEdit}
							src={business?.about_photo ? siteFileUrl('about_photo', business.about_photo.version) : null}
							photo={business?.about_photo ?? null}
							emptyPrompt="Add a photo beside your about text"
							onupload={(file) => uploadPhoto('about_photo', file)}
							onremove={() => removePhoto('about_photo')}
							onsavealt={(alt) => savePhotoAlt('about_photo', alt)}
						/>
					</div>
				{/if}
			</div>
		</SiteSection>
	{/if}

	{#if faqs.length > 0 || canEdit}
		<SiteSection tone="tint" desktopOnly={faqs.length === 0}>
			<EditableSection
				{canEdit}
				label="the questions and answers"
				isEmpty={faqs.length === 0}
				emptyPrompt="Add questions families often ask"
			>
				<div class="flex flex-col gap-6">
					<SiteHeading title="Frequently asked questions" />

					<FaqList {faqs} />
				</div>

				{#snippet editor(done)}
					<FaqEditor
						initial={faqs}
						onsubmit={(items) => save(businessApi.replaceFaqs(items), done)}
						oncancel={done}
					/>
				{/snippet}
			</EditableSection>
		</SiteSection>
	{/if}
{/if}
