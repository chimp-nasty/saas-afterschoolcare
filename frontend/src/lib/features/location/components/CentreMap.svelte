<!--
    A centre's address on an embedded Google map (docs/public-site.md, stage
    10), loaded only once it's scrolled near (loading="lazy"), with a link to
    open it in Google Maps. Without a Maps key (PUBLIC_GOOGLE_MAPS_EMBED_KEY)
    there's no map: nothing is shown and the address card's own "Open in
    maps" link does the job.
-->
<script lang="ts">
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';

	import type { PublicLocationResponse } from '$lib/api/schema';
	import { mapEmbedUrl, mapsUrl } from '../address';

	let {
		location,
		compact = false
	}: {
		location: PublicLocationResponse;
		// Shorter, without its own link (a card that has one already).
		compact?: boolean;
	} = $props();

	const src = $derived(mapEmbedUrl(location));
</script>

{#if src}
	<div class="flex flex-col gap-2">
		<iframe
			{src}
			title={`Map of ${location.location_name}`}
			class={[
				'w-full rounded-2xl border border-(--border) bg-(--surface-muted)',
				compact ? 'h-48' : 'h-72 md:h-96'
			]}
			loading="lazy"
			referrerpolicy="no-referrer-when-downgrade"
			allowfullscreen
		></iframe>

		{#if !compact}
			<div>
				<HyperTextLink href={mapsUrl(location)} external>View on map</HyperTextLink>
			</div>
		{/if}
	</div>
{/if}
