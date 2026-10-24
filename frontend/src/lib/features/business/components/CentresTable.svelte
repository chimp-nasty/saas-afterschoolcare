<!--
    The business's centres: name, address, how many services families can
    book there, and Manage centre (switches into it). Business settings'
    overview and Centres page.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import Pill from '$lib/components/text/Pill.svelte';

	import type { BusinessLocationResponse } from '$lib/api/schema';

	let {
		locations,
		onmanage,
		onedit
	}: {
		locations: BusinessLocationResponse[];
		onmanage: (location: BusinessLocationResponse) => void | Promise<void>;
		onedit?: (location: BusinessLocationResponse) => void;
	} = $props();
</script>

<GridTable
	items={locations}
	key={(location) => location.id}
	columns={onedit ? 'minmax(10rem,1.5fr) minmax(12rem,2fr) 9rem 6rem 11rem' : 'minmax(10rem,1.5fr) minmax(12rem,2fr) 9rem 11rem'}
	headers={onedit ? ['Centre', 'Address', 'Services', '', ''] : ['Centre', 'Address', 'Services', '']}
	label="Centres"
	empty="No centres yet."
>
	{#snippet row(location)}
		<span class="font-semibold">{location.name}</span>
		<span class="text-sm text-(--text-muted)">/{location.code} · {location.suburb} {location.state}</span>
		<span>
			{#if location.services_offered > 0}
				<Pill tone="success">{location.services_offered} offered</Pill>
			{:else}
				<Pill tone="warning">None offered</Pill>
			{/if}
		</span>
		{#if onedit}
			<span><Button variant="ghost" onclick={() => onedit(location)}>Edit</Button></span>
		{/if}
		<span><Button variant="ghost" onclick={() => onmanage(location)}>Manage centre</Button></span>
	{/snippet}
</GridTable>
