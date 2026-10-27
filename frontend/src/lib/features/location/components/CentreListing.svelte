<!--
    One centre on /locations: its name, the services it runs (times and ages;
    prices are on the centre's own page), where it is and how to reach it,
    and the way in. CentreCard is
    the shorter version for a single centre's details.
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import Button from '$lib/components/actions/Button.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import { agesLabel } from '$lib/features/services/policies';

	import type { LocationServiceSelectionResponse, PublicLocationResponse } from '$lib/api/schema';
	import { formatTimeRange } from '$lib/utils/helpers';
	import { addressLines, mapsUrl } from '../address';

	let {
		location,
		services
	}: {
		location: PublicLocationResponse;
		services: LocationServiceSelectionResponse[];
	} = $props();
</script>

<Card border>
	<div class="flex h-full flex-col gap-5">
		<div>
			<p class="label-text">Centre</p>

			<h2 class="text-lg font-extrabold text-(--text)">{location.location_name}</h2>
		</div>

		<div class="flex flex-col gap-3">
			{#each services as service (service.id)}
				<div class="border-b border-(--border) pb-3 last:border-b-0 last:pb-0">
					<p class="text-base font-semibold text-(--text)">{service.service_name}</p>

					<p class="text-sm text-(--text-muted)">
						{formatTimeRange(service.start_time, service.end_time)} · {agesLabel(service)}
					</p>
				</div>
			{:else}
				<EmptyState message="Services will be listed here soon." />
			{/each}
		</div>

		<div class="flex flex-col">
			{#each addressLines(location) as line}
				<p class="text-base text-(--text)">{line}</p>
			{/each}

			<div>
				<HyperTextLink href={mapsUrl(location)} external>Open in maps</HyperTextLink>
			</div>

			{#if location.phone}
				<div>
					<HyperTextLink href={`tel:${location.phone.replace(/\s/g, '')}`}>
						Call {location.phone}
					</HyperTextLink>
				</div>
			{/if}
		</div>

		<div class="mt-auto">
			<Button fullWidth onclick={() => goto(`/${location.location_code}`)}>
				Go to {location.location_name}
			</Button>
		</div>
	</div>
</Card>
