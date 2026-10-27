<!--
    The centre page's Next session card (docs/public-site.md, section 3):
    the featured service's next session that hasn't finished, and the ways
    in the page passes (`children`, e.g. Enrol now and View program). Says so
    when none are set up yet rather than showing a made-up time.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import { CalendarDays } from 'lucide-svelte';

	import Card from '$lib/components/layout/Card.svelte';

	import type { LocationServiceSelectionResponse } from '$lib/api/schema';
	import { formatDate, formatTimeRange } from '$lib/utils/helpers';

	let {
		service,
		date,
		children
	}: {
		service: LocationServiceSelectionResponse;
		// YYYY-MM-DD in the centre's time; null when none are set up.
		date: string | null;
		children?: Snippet;
	} = $props();
</script>

<Card border>
	<div class="flex h-full flex-col gap-4">
		<div class="flex items-start gap-3">
			<span class="flex size-10 shrink-0 items-center justify-center rounded-lg bg-(--accent-soft) text-(--primary)">
				<CalendarDays size={20} aria-hidden="true" />
			</span>

			<div>
				<p class="text-base font-extrabold text-(--text)">Next session</p>

				{#if date}
					<p class="text-sm text-(--text-muted)">
						{service.service_name}, {formatDate(date)}, {formatTimeRange(service.start_time, service.end_time)}
					</p>
				{:else}
					<p class="text-sm text-(--text-muted)">No {service.service_name} sessions are set up yet.</p>
				{/if}
			</div>
		</div>

		{#if children}
			<div class="mt-auto flex flex-col gap-3">
				{@render children()}
			</div>
		{/if}
	</div>
</Card>
