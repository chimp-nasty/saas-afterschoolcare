<!--
    One program on the centre's programs page (docs/public-site.md, section
    4): the service's name, ages, times and price, its description, then
    what's included, drop-off and pickup, what to bring and activities, each
    left out when empty.
-->
<script lang="ts">
	import type { LocationServiceSelectionResponse } from '$lib/api/schema';
	import { formatMoney, formatTimeRange } from '$lib/utils/helpers';
	import { agesLabel } from '../policies';
	import { programParts } from '../program';

	let {
		service
	}: {
		service: LocationServiceSelectionResponse;
	} = $props();

	const parts = $derived(programParts(service));
</script>

<article class="flex flex-col gap-6">
	<div class="flex flex-col gap-2">
		<h2 class="headline-text">{service.service_name}</h2>

		<p class="text-base text-(--text-muted)">
			{agesLabel(service)} · {formatTimeRange(service.start_time, service.end_time)} ·
			{formatMoney(service.current_price_cents, service.currency)} a session
		</p>
	</div>

	{#if service.description}
		<p class="max-w-3xl whitespace-pre-line text-base text-(--text) md:text-lg">{service.description}</p>
	{/if}

	{#if parts.length > 0}
		<div class="grid gap-6 md:grid-cols-2">
			{#each parts as part (part.field)}
				<div class="flex flex-col gap-2">
					<p class="label-text">{part.label}</p>
					<p class="whitespace-pre-line text-base text-(--text)">{part.text}</p>
				</div>
			{/each}
		</div>
	{/if}
</article>
