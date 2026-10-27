<!--
    /locations (docs/public-site.md): every centre, with where it is and the
    services it runs, and a way into each. Stage 8 links each centre's
    programs; stage 10 adds a map.
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import CentreListing from '$lib/features/location/components/CentreListing.svelte';

	let { data } = $props();
</script>

<SiteSection>
	<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
		<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

		<p class="label-text">Locations</p>

		<h1 class="display-text">Our centres</h1>

		<p class="text-base text-(--text-muted) md:text-lg">
			Choose your centre to see its services and book.
		</p>
	</div>
</SiteSection>

<SiteSection tone="muted">
	{#if data.locations.length > 0}
		<div class="grid gap-4 md:grid-cols-2">
			{#each data.locations as location (location.location_code)}
				<CentreListing {location} services={data.servicesByCentre[location.location_code] ?? []} />
			{/each}
		</div>
	{:else}
		<Card border>
			<EmptyState message="We couldn't find any centres here. Use the link your centre gave you." />
		</Card>
	{/if}
</SiteSection>
