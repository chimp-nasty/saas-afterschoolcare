<!--
    The staff and admin home: what needs attention at the location. Starts
    with medical reviews; each slice adds its own cards
    (docs/staff-platform.md).
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';

	let {
		locationCode,
		reviewsWaiting,
		reviewsRequested
	}: {
		locationCode: string;
		// Children waiting for staff, and waiting on their family.
		reviewsWaiting: number;
		reviewsRequested: number;
	} = $props();
</script>

<PageHeader title="Home" />

<section class="flex flex-col gap-4">
	<h2 class="text-lg font-extrabold text-(--text)">
		Needs attention
	</h2>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
		<Card border href={`/${locationCode}/staff/reviews`}>
			<div class="flex flex-col gap-1">
				<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">
					Medical reviews
				</p>

				<p class="text-2xl font-extrabold text-(--text)">
					{reviewsWaiting}
				</p>

				<p class="text-sm text-(--text-muted)">
					{reviewsWaiting === 1 ? 'child' : 'children'} waiting for review{reviewsRequested
						? ` · ${reviewsRequested} waiting on documents`
						: ''}
				</p>
			</div>
		</Card>
	</div>
</section>
