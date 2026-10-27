<!--
    The business's landing page ("/", docs/public-site.md): its headline, its
    centres (each a way in; all of them on /locations), a taste of its about
    text (the rest on /about) and its FAQs. All set by its owner in Business
    settings; a section with nothing to show is left out. The header and
    footer are the layout's. On the platform's own site, a placeholder.
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import Highlights from '$lib/features/business/components/Highlights.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';

	let { data } = $props();

	// At most this many centres here; the rest are on /locations.
	const CENTRES_SHOWN = 3;
	// About this long here, then "More about us".
	const ABOUT_TASTE = 280;

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Choose your centre');

	const aboutTaste = $derived.by(() => {
		const about = business?.about ?? '';

		return about.length > ABOUT_TASTE ? `${about.slice(0, ABOUT_TASTE).trimEnd()}…` : about;
	});
</script>

{#if data.platform}
	<main class="p-4">
		<!-- The platform's own site: no business here. -->
		<Page>
			<PageHeader title="After school care bookings" description="Businesses sign up by invitation." />

			<HyperTextLink href="/platform/login">Platform login</HyperTextLink>
		</Page>
	</main>
{:else}
	<!-- The hero: the business's headline and paragraph, then its
	     highlights (stage 9 adds its photo). -->
	<SiteSection>
		<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
			<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

			{#if business?.tagline}
				<p class="label-text">{name}</p>
			{/if}

			<h1 class="display-text">{business?.tagline ?? name}</h1>

			<p class="text-base text-(--text-muted) md:text-lg">
				{business?.hero_text ?? 'Choose your centre to see its services and book.'}
			</p>

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

		{#if business && business.highlights.length > 0}
			<div class="border-t border-(--border) pt-8">
				<Highlights highlights={business.highlights} />
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
				<EmptyState message="We couldn't find any centres here. Use the link your centre gave you." />
			</Card>
		{/if}
	</SiteSection>

	{#if business?.about}
		<SiteSection>
			<SiteHeading title={`About ${name}`} />

			<p class="max-w-3xl whitespace-pre-line text-base text-(--text) md:text-lg">{aboutTaste}</p>

			<div>
				<HyperTextLink href="/about">More about us</HyperTextLink>
			</div>
		</SiteSection>
	{/if}

	{#if business && business.faqs.length > 0}
		<SiteSection tone="tint">
			<SiteHeading title="Frequently asked questions" />

			<div class="max-w-3xl">
				<Card border padded={false}>
					{#each business.faqs as faq, index (index)}
						<details class="group border-b border-(--border) last:border-b-0">
							<summary class="flex min-h-12 cursor-pointer items-center px-5 py-3 text-base font-semibold text-(--text)">
								{faq.question}
							</summary>

							<p class="whitespace-pre-line px-5 pb-4 text-base text-(--text)">{faq.answer}</p>
						</details>
					{/each}
				</Card>
			</div>
		</SiteSection>
	{/if}
{/if}
