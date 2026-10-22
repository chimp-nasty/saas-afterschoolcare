<!--
    The admin home: what needs attention at the location, linking into the
    admin portal. Staff-role logins never see it; their home is their
    account (docs/portals.md).
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	let {
		locationCode,
		reviewsWaiting,
		reviewsRequested,
		latePickups
	}: {
		locationCode: string;
		// Children waiting for staff, and waiting on their family.
		reviewsWaiting: number;
		reviewsRequested: number;
		// Children still signed in after their session ended today.
		latePickups: number;
	} = $props();
</script>

<PageHeader title="Home" />

<section class="flex flex-col gap-4">
	<SectionHeading title="Needs attention" />

	<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
		<Card border href={`/${locationCode}/admin/run-sheet`}>
			<div class="flex flex-col gap-1">
				<p class="label-text">
					Late pickups
				</p>

				<p class={['text-2xl font-extrabold', latePickups ? 'text-(--danger-text)' : 'text-(--text)']}>
					{latePickups}
				</p>

				<p class="text-sm text-(--text-muted)">
					{latePickups === 1 ? 'child' : 'children'} still here after their session ended
				</p>
			</div>
		</Card>

		<Card border href={`/${locationCode}/admin/reviews`}>
			<div class="flex flex-col gap-1">
				<p class="label-text">
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
