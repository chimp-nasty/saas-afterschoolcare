<!--
    The centre page hero's facts row (docs/public-site.md, section 3): where
    it is, when its featured service runs ("After School Care · 3:00pm –
    6:00pm · Mon–Fri") and who it's for. A fact with nothing to say is left
    out; the address always has something.
-->
<script lang="ts">
	import { Clock, MapPin, Users } from 'lucide-svelte';

	import type { LocationServiceSelectionResponse, PublicLocationResponse } from '$lib/api/schema';
	import { agesLabel } from '$lib/features/services/policies';
	import { formatTimeRange, formatWeekdays } from '$lib/utils/helpers';

	let {
		location,
		service,
		weekdays
	}: {
		location: PublicLocationResponse;
		// The featured service (none when the centre offers nothing yet).
		service: LocationServiceSelectionResponse | null;
		weekdays: number[];
	} = $props();

	const when = $derived(
		service
			? [service.service_name, formatTimeRange(service.start_time, service.end_time), formatWeekdays(weekdays)]
					.filter(Boolean)
					.join(' · ')
			: null
	);
</script>

<ul class="flex flex-col gap-3 text-sm text-(--text) md:flex-row md:flex-wrap md:gap-x-8">
	<li class="flex items-center gap-2">
		<MapPin size={18} class="shrink-0 text-(--primary)" aria-hidden="true" />
		<span>{location.address_line_1}, {location.suburb}</span>
	</li>

	{#if service && when}
		<li class="flex items-center gap-2">
			<Clock size={18} class="shrink-0 text-(--primary)" aria-hidden="true" />
			<span>{when}</span>
		</li>

		<li class="flex items-center gap-2">
			<Users size={18} class="shrink-0 text-(--primary)" aria-hidden="true" />
			<span>{agesLabel(service)}</span>
		</li>
	{/if}
</ul>
