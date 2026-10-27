<!--
    /about (docs/public-site.md): the business's about text and how to reach
    it, both set by its owner in Business settings. A fuller page (photos,
    sections) may come later.
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';

	let { data } = $props();

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Us');

	const hasContact = $derived(Boolean(business?.email || business?.phone));
</script>

<SiteSection>
	<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
		<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

		<p class="label-text">About</p>

		<h1 class="display-text">{name}</h1>

		{#if business?.about}
			<p class="whitespace-pre-line text-base text-(--text) md:text-lg">{business.about}</p>
		{:else}
			<EmptyState message="More about us soon." />
		{/if}
	</div>
</SiteSection>

{#if business && hasContact}
	<SiteSection tone="muted">
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
