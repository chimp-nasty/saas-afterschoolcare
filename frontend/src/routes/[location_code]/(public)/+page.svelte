<!--
    The centre's page (docs/public-site.md, section 3), service first: the
    business's headline under the centre's name and the ways in, the facts
    (where, when, who), the highlights beside the next session, about the
    program, the services (with prices), where to find it and the FAQs.
    The business's owner edits the words in place on desktop (the same text
    as the landing page: EditableSection, section 6). A section with nothing
    to show is left out.
-->
<script lang="ts">
	import { goto, invalidate } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import AboutForm from '$lib/features/business/components/AboutForm.svelte';
	import FaqEditor from '$lib/features/business/components/FaqEditor.svelte';
	import FaqList from '$lib/features/business/components/FaqList.svelte';
	import HeroForm from '$lib/features/business/components/HeroForm.svelte';
	import HighlightEditor from '$lib/features/business/components/HighlightEditor.svelte';
	import Highlights from '$lib/features/business/components/Highlights.svelte';
	import SitePhoto from '$lib/features/business/components/SitePhoto.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';
	import CentreFacts from '$lib/features/location/components/CentreFacts.svelte';
	import CentreMap from '$lib/features/location/components/CentreMap.svelte';
	import NextSessionCard from '$lib/features/services/components/NextSessionCard.svelte';
	import ServiceCard from '$lib/features/services/components/ServiceCard.svelte';

	import { auth } from '$lib/auth/state.svelte';
	import { logout } from '$lib/auth/logout';
	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import { centrePhotoUrl, siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { ApiResponse } from '$lib/api/wrapper';
	import EditablePhoto from '$lib/features/business/components/EditablePhoto.svelte';
	import { uploadPhoto } from '$lib/features/business/siteFiles';

	let { data } = $props();

	const businessApi = createBusinessApi();

	// About this long here, then "More about us".
	const ABOUT_TASTE = 280;

	const name = $derived(data.location.location_name);
	const business = $derived(data.business);
	const canEdit = $derived(data.isOwner);

	const highlights = $derived(business?.highlights ?? []);
	const faqs = $derived(business?.faqs ?? []);

	// The service the page leads with (the featured one, else the first
	// offered): its details are in the services list.
	const featured = $derived(
		data.featured
			? (data.services.find((service) => service.id === data.featured?.location_service_id) ?? null)
			: null
	);

	const isFamily = $derived($auth.authenticated && $auth.roles.includes('customer'));

	const aboutTaste = $derived.by(() => {
		const about = business?.about ?? '';

		return about.length > ABOUT_TASTE ? `${about.slice(0, ABOUT_TASTE).trimEnd()}…` : about;
	});

	function route(path: string) {
		return `/${data.locationCode}${path}`;
	}

	// The main way in: enrolling, or booking once a family is logged in here.
	const mainAction = $derived(
		isFamily
			? { label: 'Book a session', href: route('/bookings/new') }
			: $auth.authenticated
				? { label: 'Go to home', href: route('/home') }
				: { label: 'Enrol now', href: route('/register') }
	);

	// The hero's photo (stage 9b): the centre's own, else the business's.
	// The owner sets the centre's, like its other details.
	const businessHeroPhoto = $derived(
		business?.hero_photo
			? {
					src: siteFileUrl('hero_photo', business.hero_photo.version),
					alt: business.hero_photo.alt,
					note: "No photo of this centre yet: your business's photo shows here."
				}
			: null
	);
	const heroPhotoShown = $derived(Boolean(data.location.photo || businessHeroPhoto));
	const heroPhotoColumn = $derived(heroPhotoShown || canEdit);

	async function uploadCentrePhoto(file: File) {
		const ok = await uploadPhoto(
			file,
			(contentType) => businessApi.startCentrePhotoUpload(data.location.location_id, contentType),
			(key) => businessApi.confirmCentrePhotoUpload(data.location.location_id, key)
		);

		if (ok) await invalidate('app:location');

		return ok;
	}

	async function removeCentrePhoto() {
		const response = await businessApi.removeCentrePhoto(data.location.location_id);

		if (response.ok) await invalidate('app:location');
	}

	async function saveCentrePhotoAlt(alt: string | null) {
		const response = await businessApi.updateCentrePhotoAlt(data.location.location_id, alt);

		if (response.ok) await invalidate('app:location');

		return response;
	}

	// Save a section, then show the page's new content in its place.
	async function save<T>(response: Promise<ApiResponse<T>>, done: () => void) {
		const result = await response;

		if (result.ok) {
			await invalidate('app:business-site');
			done();
		}

		return result;
	}
</script>

<!-- The hero: the centre, the business's headline and the ways in beside
     the centre's photo (else the business's), then the facts. -->
<SiteSection>
	<div class={['grid gap-10 lg:items-center', heroPhotoColumn && 'lg:grid-cols-2']}>
		<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
			<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

			<p class="label-text">{name}</p>

			<EditableSection {canEdit} label="the headline">
				<div class="flex flex-col gap-5 pr-14">
					<h1 class="display-text">{business?.tagline ?? name}</h1>

					<p class="text-base text-(--text-muted) md:text-lg">
						{business?.hero_text ?? 'See what we offer, then book and pay online.'}
					</p>
				</div>

				{#snippet editor(done)}
					<HeroForm
						initial={{ tagline: business?.tagline ?? null, hero_text: business?.hero_text ?? null }}
						onsubmit={(body) => save(businessApi.updateSite(body), done)}
						oncancel={done}
					/>
				{/snippet}
			</EditableSection>

			{#if data.signedInElsewhere}
				<!-- Logged in at another of the tenant's centres; that session
			     doesn't count here (routes/[location_code]/+layout.ts). -->
				<Notice>
					You're logged in at {data.signedInElsewhere.locationName}. Log out to use this centre
					instead.
				</Notice>

				<ActionBar start>
					<Button variant="ghost" onclick={() => logout(data.locationCode)}>Log out</Button>

					<Button onclick={() => goto(`/${data.signedInElsewhere?.locationCode}/home`)}>
						Go to {data.signedInElsewhere.locationName}
					</Button>
				</ActionBar>
			{:else}
				<ActionBar start>
					<Button variant="ghost" onclick={() => goto(route('/programs'))}>View program</Button>
					<Button onclick={() => goto(mainAction.href)}>{mainAction.label}</Button>
				</ActionBar>
			{/if}
		</div>

		{#if heroPhotoColumn}
			<div class={[!heroPhotoShown && 'hidden md:block']}>
				<EditablePhoto
					{canEdit}
					photo={data.location.photo ?? null}
					src={data.location.photo
						? centrePhotoUrl(data.locationCode, data.location.photo.version)
						: null}
					fallback={businessHeroPhoto}
					emptyPrompt={`Add a photo of ${name}`}
					onupload={uploadCentrePhoto}
					onremove={removeCentrePhoto}
					onsavealt={saveCentrePhotoAlt}
				/>
			</div>
		{/if}
	</div>

	<div class="border-t border-(--border) pt-6">
		<CentreFacts
			location={data.location}
			service={featured}
			weekdays={data.featured?.weekdays ?? []}
		/>
	</div>
</SiteSection>

<!-- The highlights beside the next session (on a phone, the card after
     them). -->
{#if highlights.length > 0 || featured || canEdit}
	<SiteSection tone="muted" desktopOnly={highlights.length === 0 && !featured}>
		<div class="grid gap-8 lg:grid-cols-[minmax(0,3fr)_minmax(16rem,1fr)] lg:items-start">
			<div class={[highlights.length === 0 && 'hidden md:block']}>
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

			{#if featured}
				<NextSessionCard service={featured} date={data.featured?.next_session_date ?? null}>
					<Button fullWidth onclick={() => goto(mainAction.href)}>{mainAction.label}</Button>
					<Button variant="ghost" fullWidth onclick={() => goto(route('/programs'))}
						>View program</Button
					>
					<HyperTextLink href="#find-us">Location details</HyperTextLink>
				</NextSessionCard>
			{/if}
		</div>
	</SiteSection>
{/if}

<!-- About the program: the business's about text and this centre's
     services, each linking to its program. -->
{#if business?.about || data.services.length > 0 || canEdit}
	<SiteSection>
		<div class="grid gap-8 lg:grid-cols-2">
			<EditableSection
				{canEdit}
				label="your about text"
				isEmpty={!business?.about}
				emptyPrompt="Add a few words about your business"
			>
				<div class="flex flex-col gap-6 pr-14">
					<SiteHeading title={`About ${business?.name ?? data.location.tenant_name}`} />

					<p class="text-base whitespace-pre-line text-(--text) md:text-lg">{aboutTaste}</p>

					<div>
						<HyperTextLink href="/about">More about us</HyperTextLink>
					</div>

					{#if business?.about_photo}
						<SitePhoto
							src={siteFileUrl('about_photo', business.about_photo.version)}
							alt={business.about_photo.alt}
						/>
					{/if}
				</div>

				{#snippet editor(done)}
					<AboutForm
						initial={business?.about ?? null}
						onsubmit={(body) => save(businessApi.updateSite(body), done)}
						oncancel={done}
					/>
				{/snippet}
			</EditableSection>

			{#if data.services.length > 0}
				<div class="flex flex-col gap-4">
					<p class="label-text">Programs offered</p>

					<ul class="flex flex-col">
						{#each data.services as service (service.id)}
							<li class="border-b border-(--border) last:border-b-0">
								<a
									href={route(`/programs#${service.id}`)}
									class="flex min-h-12 items-center justify-between gap-4 text-base font-semibold text-(--text) hover:text-(--primary)"
								>
									{service.service_name}
									<span class="text-sm font-semibold text-(--text-muted)"
										>{service.age_label ?? ''}</span
									>
								</a>
							</li>
						{/each}
					</ul>
				</div>
			{/if}
		</div>
	</SiteSection>
{/if}

<SiteSection id="services" tone="muted">
	<SiteHeading title="Our services" />

	{#if data.services.length > 0}
		<div class="grid gap-4 md:grid-cols-2">
			{#each data.services as service (service.id)}
				<ServiceCard {service} />
			{/each}
		</div>
	{:else}
		<EmptyState message="Services will be listed here soon." />
	{/if}
</SiteSection>

<!-- Find us: the address card beside the map (stage 10; without a Maps
     key, just the card). -->
<SiteSection id="find-us">
	<SiteHeading title="Find us" />

	<div class="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)] lg:items-start">
		<div class="max-w-xl">
			<CentreCard location={data.location} />
		</div>

		<CentreMap location={data.location} />
	</div>
</SiteSection>

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
