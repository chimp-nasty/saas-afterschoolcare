<!--
    The business's landing page ("/", docs/tenant-administration.md stage 5):
    its logo and headline, its centres (each a way in), about, FAQs, how to
    reach it, and its policies. All set by its owner in Business settings;
    a section with nothing to show is left out. Business settings isn't
    linked from here. On the platform's own site, a placeholder instead.
-->
<script lang="ts">
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';

	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';

	let { data } = $props();

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Choose your centre');

	const hasContact = $derived(Boolean(business?.email || business?.phone));

	// The page's own menu: only sections it has.
	const sections = $derived(
		[
			{ id: 'centres', label: 'Centres', show: true },
			{ id: 'about', label: 'About', show: Boolean(business?.about) },
			{ id: 'faqs', label: 'FAQs', show: (business?.faqs.length ?? 0) > 0 },
			{ id: 'contact', label: 'Contact', show: hasContact }
		].filter((section) => section.show)
	);
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
	<Layout primaryColor={business?.primary_color} secondaryColor={business?.secondary_color}>
		{#snippet header()}
			<header class="w-full border-b border-(--border) bg-(--surface) p-4">
				<div class="mx-auto flex max-w-xl flex-col gap-3">
					<div class="flex min-h-12 items-center gap-3">
						{#if business?.has_logo}
							<img src={siteFileUrl('logo')} alt="" class="h-10 w-auto max-w-40 object-contain" />
						{/if}

						<p class="text-lg font-extrabold text-(--text)">{name}</p>
					</div>

					{#if sections.length > 1}
						<nav class="flex flex-wrap gap-x-5">
							{#each sections as section (section.id)}
								<HyperTextLink href={`#${section.id}`}>{section.label}</HyperTextLink>
							{/each}
						</nav>
					{/if}
				</div>
			</header>
		{/snippet}

		<Page>
			<PageHeader
				title={business?.tagline ?? name}
				description={business?.tagline ? undefined : 'Choose your centre to see its services and book.'}
			/>

			<section id="centres" class="flex scroll-mt-4 flex-col gap-4">
				<SectionHeading title="Our centres" />

				{#each data.locations as location (location.location_code)}
					<CentreCard {location} href={`/${location.location_code}`} />
				{:else}
					<Card border>
						<EmptyState message="We couldn't find any centres here. Use the link your centre gave you." />
					</Card>
				{/each}
			</section>

			{#if business?.about}
				<section id="about" class="flex scroll-mt-4 flex-col gap-4">
					<SectionHeading title={`About ${name}`} />

					<p class="whitespace-pre-line text-base text-(--text)">{business.about}</p>
				</section>
			{/if}

			{#if business && business.faqs.length > 0}
				<section id="faqs" class="flex scroll-mt-4 flex-col gap-4">
					<SectionHeading title="Frequently asked questions" />

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
				</section>
			{/if}

			{#if business && hasContact}
				<section id="contact" class="flex scroll-mt-4 flex-col gap-4">
					<SectionHeading title="Contact" description="Each centre's address and phone are on its page." />

					<Card border>
						<LabelValueList
							items={[
								{ label: 'Email', value: business.email },
								{ label: 'Phone', value: business.phone }
							]}
						/>
					</Card>
				</section>
			{/if}
		</Page>

		{#snippet footer()}
			<div class="mx-auto flex max-w-xl flex-col gap-2 p-4">
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

				<p class="text-sm text-(--text-muted)">© {new Date().getFullYear()} {name}</p>
			</div>
		{/snippet}
	</Layout>
{/if}
