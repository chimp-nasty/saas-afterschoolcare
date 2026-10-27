<!--
    An error loading a page at this location. Not found: go home (or to the
    landing page). Anything else: say so, rather than hiding it.
-->
<script lang="ts">
	import { goto } from '$app/navigation';
	import Button from '$lib/components/actions/Button.svelte';
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import { onMount } from 'svelte';
	import { page } from '$app/state';

	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';

	import { leaveMissingPage } from '$lib/navigation/not-found';

	const locationCode = $derived(page.params.location_code ?? '');
	const isLoggedIn = $derived(Boolean(page.data.session));

	onMount(() => {
		if (page.status === 404) {
			void leaveMissingPage(locationCode, isLoggedIn);
		}
	});
</script>

{#if page.status !== 404}
	<Page>
		<PageHeader title="Something went wrong" description={page.error?.message} />

		<Card border>
			<p class="text-sm text-(--text-muted)">
				Try again in a moment. If it keeps happening, contact the centre.
			</p>

			<ActionBar start>
				<Button variant="ghost" onclick={() => goto(isLoggedIn ? `/${locationCode}/home` : `/${locationCode}`)}>Back to home</Button>
			</ActionBar>
		</Card>
	</Page>
{/if}
