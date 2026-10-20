<!--
    The tenant's landing page ("/"): its centres, each a card to choose.
    A simple placeholder until tenant setup is built.
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';

	let { data } = $props();

	const tenantName = $derived(data.locations[0]?.tenant_name);
</script>

<main class="p-4">
	<Page>
		<PageHeader
			title={tenantName ?? 'Choose your centre'}
			description={tenantName ? 'Choose your centre to see its services and book.' : undefined}
		/>

		{#each data.locations as location (location.location_code)}
			<CentreCard {location} href={`/${location.location_code}`} />
		{:else}
			<Card border>
				<p class="text-sm text-(--text-muted)">
					We couldn't find any centres here. Use the link your centre gave you.
				</p>
			</Card>
		{/each}
	</Page>
</main>
