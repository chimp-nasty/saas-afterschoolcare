<!--
    The business's landing page ("/", docs/tenant-administration.md stage 5):
    its logo and headline, its centres (each a way in), about, FAQs, how to
    reach it, and its policies. All set by its owner in Business settings;
    a section with nothing to show is left out. Business settings isn't
    linked from here. On the platform's own site, a placeholder instead.
    Laid out as the public site's bands (docs/public-site.md); the header
    is replaced in stage 2.
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
	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';

	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';

	let { data } = $props();

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Choose your centre');

	const hasContact = $derived(Boolean(business?.email || business?.phone));

	// The business pages' header (docs/public-site.md, section 2): no
	// Programs, since they're each centre's. Locations and About are this
	// page's sections until their own pages exist (stage 3).
	const headerLinks = $derived([
		{ label: 'Locations', href: '#centres' },
		...(business?.about ? [{ label: 'About', href: '#about' }] : [])
	]);

	// Logging in and enrolling happen at a centre: straight there when
	// there's only one, otherwise choose one first.
	const onlyCentre = $derived(data.locations.length === 1 ? data.locations[0].location_code : null);
	const loginHref = $derived(onlyCentre ? `/${onlyCentre}/login` : '#centres');
	const enrolHref = $derived(onlyCentre ? `/${onlyCentre}/register` : '#centres');
</script>

{#snippet getStarted()}
	<Button variant="ghost" onclick={() => goto(loginHref)}>Log in</Button>
	<Button onclick={() => goto(enrolHref)}>Enrol now</Button>
{/snippet}


{#if data.platform}
	<main class="p-4">
		<!-- The platform's own site: no business here. -->
		<Page>
			<PageHeader title="After school care bookings" description="Businesses sign up by invitation." />

			<HyperTextLink href="/platform/login">Platform login</HyperTextLink>
		</Page>
	</main>
{:else}
	<Layout
		flush
		primaryColor={business?.primary_color}
		secondaryColor={business?.secondary_color}
		accentColor={business?.accent_color}
	>
		{#snippet header()}
			<Header
				homeHref="/"
				title={name}
				hasLogo={Boolean(business?.has_logo)}
				links={headerLinks}
				menuItems={data.locations.length > 0
					? [
							{ label: 'Log in', href: loginHref },
							{ label: 'Enrol now', href: enrolHref }
						]
					: []}
				desktopActions={data.locations.length > 0 ? getStarted : undefined}
				flush
			/>
		{/snippet}

		<!-- The hero: the business's headline (stage 4 adds its own text,
		     highlights and photo). -->
		<SiteSection>
			<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
				<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

				{#if business?.tagline}
					<p class="label-text">{name}</p>
				{/if}

				<h1 class="display-text">{business?.tagline ?? name}</h1>

				<p class="text-base text-(--text-muted) md:text-lg">
					Choose your centre to see its services and book.
				</p>

				{#if data.locations.length > 0}
					<ActionBar start>
						{#if data.locations.length === 1}
							<Button onclick={() => goto(`/${data.locations[0].location_code}`)}>
								Go to {data.locations[0].location_name}
							</Button>
						{:else}
							<Button onclick={() => goto('#centres')}>Find your centre</Button>
						{/if}
					</ActionBar>
				{/if}
			</div>
		</SiteSection>

		<SiteSection id="centres" tone="muted">
			<SiteHeading title="Our centres" />

			{#if data.locations.length > 0}
				<div class="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
					{#each data.locations as location (location.location_code)}
						<CentreCard {location} href={`/${location.location_code}`} />
					{/each}
				</div>
			{:else}
				<Card border>
					<EmptyState message="We couldn't find any centres here. Use the link your centre gave you." />
				</Card>
			{/if}
		</SiteSection>

		{#if business?.about}
			<SiteSection id="about">
				<SiteHeading title={`About ${name}`} />

				<p class="max-w-3xl whitespace-pre-line text-base text-(--text) md:text-lg">{business.about}</p>
			</SiteSection>
		{/if}

		{#if business && business.faqs.length > 0}
			<SiteSection id="faqs" tone="tint">
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

		{#if business && hasContact}
			<SiteSection id="contact">
				<SiteHeading title="Contact" description="Each centre's address and phone are on its page." />

				<div class="max-w-xl">
					<Card border>
						<LabelValueList
							items={[
								{ label: 'Email', value: business.email },
								{ label: 'Phone', value: business.phone }
							]}
						/>
					</Card>
				</div>
			</SiteSection>
		{/if}

		{#snippet footer()}
			<div class="w-full border-t border-(--border) bg-(--surface) px-4 py-8">
				<div class="mx-auto flex max-w-6xl flex-col gap-2 md:flex-row md:items-center md:justify-between">
					<p class="text-sm text-(--text-muted)">© {new Date().getFullYear()} {name}</p>

					{#if business?.has_privacy || business?.has_terms}
						<div class="flex flex-wrap gap-x-5">
							{#if business.has_privacy}
								<HyperTextLink href={siteFileUrl('privacy')} external>Privacy policy</HyperTextLink>
							{/if}
							{#if business.has_terms}
								<HyperTextLink href={siteFileUrl('terms')} external>Terms</HyperTextLink>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{/snippet}
	</Layout>
{/if}
