<!--
    The platform's own home page (docs/platform-site.md): what Session Pilot
    is, for businesses that run outside school hours care, and the way to
    talk to us (Book a demo opens the contact page on "for my own
    business"). The hero, feature cards and about band are the platform's
    (public.platform_site), edited in place by its admins like a business's
    site; the steps are written here. Holds no data and saves nothing: the
    page passes the content and what to do with each edit.
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import EditablePhoto from '$lib/features/business/components/EditablePhoto.svelte';
	import PlatformFeatureEditor from './PlatformFeatureEditor.svelte';
	import PlatformFeatures from './PlatformFeatures.svelte';
	import PlatformTextForm from './PlatformTextForm.svelte';

	import { platformFileUrl } from '$lib/api/platform/adapters/platformSite';
	import type { PlatformFeatureItem, PlatformSiteRequest, PlatformSiteResponse } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';
	import { PLATFORM_CONTACT_HREF, PLATFORM_NAME } from '$lib/platform/site';

	type PhotoKind = 'hero_photo' | 'about_photo';

	let {
		site,
		canEdit,
		onsave,
		onsavefeatures,
		onupload,
		onremove
	}: {
		site: PlatformSiteResponse | null;
		// A platform admin, logged in.
		canEdit: boolean;
		// Each resolves once saved (the section's editor then closes).
		onsave: (body: PlatformSiteRequest, done: () => void) => Promise<ApiResponse<unknown>>;
		onsavefeatures: (features: PlatformFeatureItem[], done: () => void) => Promise<ApiResponse<unknown>>;
		onupload: (kind: PhotoKind, file: File) => Promise<boolean>;
		onremove: (kind: PhotoKind) => Promise<void>;
	} = $props();

	const DEMO_HREF = `${PLATFORM_CONTACT_HREF}?topic=own_business`;

	const STEPS = [
		{ title: 'Talk to us', body: "Tell us about your business. We'll show you around and help you onboard." },
		{ title: 'Add your locations', body: 'Your programs, session times and prices, and connect Stripe to take payments.' },
		{ title: 'Share your site', body: 'Families register, add their children and book. You run the day from the kiosk and admin.' }
	];

	const features = $derived(site?.features ?? []);

	// Room for a photo when there is one, or an admin may add one.
	const heroPhotoColumn = $derived(Boolean(site?.hero_photo) || canEdit);
	const aboutPhotoColumn = $derived(Boolean(site?.about_photo) || canEdit);
</script>

<!-- The hero: the headline and paragraph beside the photo. -->
<SiteSection>
	<div class={['grid gap-10 lg:items-center', heroPhotoColumn && 'lg:grid-cols-2']}>
		<div class="flex max-w-3xl flex-col gap-6 py-6 md:py-12">
			<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

			<EditableSection {canEdit} label="the headline">
				<div class="flex flex-col gap-6 pr-14">
					<p class="label-text">{PLATFORM_NAME}</p>

					<h1 class="display-text">{site?.headline ?? 'Simple software for outside school hours care'}</h1>

					{#if site?.hero_text}
						<p class="text-lg text-(--text-muted) md:text-xl">{site.hero_text}</p>
					{/if}
				</div>

				{#snippet editor(done)}
					<PlatformTextForm
						fields={['headline', 'hero_text']}
						labels={['Headline', 'Under the headline: a sentence or two']}
						initial={[site?.headline ?? null, site?.hero_text ?? null]}
						textMax={300}
						onsubmit={(body) => onsave(body, done)}
						oncancel={done}
					/>
				{/snippet}
			</EditableSection>

			<ActionBar start>
				<Button onclick={() => goto(DEMO_HREF)}>Book a demo</Button>
				<Button variant="ghost" onclick={() => goto(PLATFORM_CONTACT_HREF)}>Talk to us</Button>
			</ActionBar>
		</div>

		{#if heroPhotoColumn}
			<div class={[!site?.hero_photo && 'hidden md:block']}>
				<EditablePhoto
					{canEdit}
					src={site?.hero_photo ? platformFileUrl('hero_photo', site.hero_photo.version) : null}
					photo={site?.hero_photo ?? null}
					emptyPrompt="Add a photo beside the headline"
					shape="wave"
					onupload={(file) => onupload('hero_photo', file)}
					onremove={() => onremove('hero_photo')}
					onsavealt={(alt) => onsave({ hero_photo_alt: alt }, () => {})}
				/>
			</div>
		{/if}
	</div>
</SiteSection>

{#if features.length > 0 || canEdit}
	<SiteSection tone="muted" desktopOnly={features.length === 0}>
		<EditableSection
			{canEdit}
			label="the features"
			isEmpty={features.length === 0}
			emptyPrompt="Add the feature cards"
		>
			<div class="flex flex-col gap-6">
				<SiteHeading
					title="Everything a centre runs on"
					description="Built to support your data compliance obligations."
				/>

				<PlatformFeatures {features} />
			</div>

			{#snippet editor(done)}
				<PlatformFeatureEditor
					initial={features}
					onsubmit={(items) => onsavefeatures(items, done)}
					oncancel={done}
				/>
			{/snippet}
		</EditableSection>
	</SiteSection>
{/if}

{#if site?.about || canEdit}
	<SiteSection desktopOnly={!site?.about}>
		<div class={['grid gap-10 lg:items-center', aboutPhotoColumn && 'lg:grid-cols-2']}>
			{#if aboutPhotoColumn}
				<div class={[!site?.about_photo && 'hidden md:block']}>
					<EditablePhoto
						{canEdit}
						src={site?.about_photo ? platformFileUrl('about_photo', site.about_photo.version) : null}
						photo={site?.about_photo ?? null}
						emptyPrompt="Add a photo beside the about text"
						onupload={(file) => onupload('about_photo', file)}
						onremove={() => onremove('about_photo')}
						onsavealt={(alt) => onsave({ about_photo_alt: alt }, () => {})}
					/>
				</div>
			{/if}

			<EditableSection
				{canEdit}
				label="the about text"
				isEmpty={!site?.about}
				emptyPrompt="Add a few words about the software"
			>
				<div class="flex flex-col gap-6 pr-14">
					<SiteHeading title={site?.about_title ?? `About ${PLATFORM_NAME}`} />

					<p class="max-w-3xl text-base whitespace-pre-line text-(--text) md:text-lg">{site?.about}</p>

					<ActionBar start>
						<Button onclick={() => goto(DEMO_HREF)}>Book a demo</Button>
					</ActionBar>
				</div>

				{#snippet editor(done)}
					<PlatformTextForm
						fields={['about_title', 'about']}
						labels={['Title', 'About the software']}
						initial={[site?.about_title ?? null, site?.about ?? null]}
						textMax={1000}
						onsubmit={(body) => onsave(body, done)}
						oncancel={done}
					/>
				{/snippet}
			</EditableSection>
		</div>
	</SiteSection>
{/if}

<SiteSection tone="muted">
	<div class="flex flex-col gap-6">
		<SiteHeading title="Getting started" />

		<ol class="grid grid-cols-1 gap-4 md:grid-cols-3">
			{#each STEPS as step, index (step.title)}
				<li class="flex flex-col gap-2">
					<span class="flex size-10 items-center justify-center rounded-full bg-(--primary-soft) text-lg font-extrabold text-(--primary)">
						{index + 1}
					</span>
					<p class="text-lg font-extrabold text-(--text)">{step.title}</p>
					<p class="text-base text-(--text-muted)">{step.body}</p>
				</li>
			{/each}
		</ol>
	</div>
</SiteSection>

<SiteSection tone="tint">
	<div class="flex flex-col gap-5">
		<h2 class="headline-text">Interested in SessionPilot for your own business?</h2>

		<ActionBar start>
			<Button onclick={() => goto(DEMO_HREF)}>Book a demo</Button>
		</ActionBar>
	</div>
</SiteSection>
