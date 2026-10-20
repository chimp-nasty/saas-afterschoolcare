<!--
    An error above any location: usually a location that doesn't exist. Not
    found goes to the tenant's page ("/"), never from "/" itself, so it can't
    loop. Anything else is shown.
-->
<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';

	const redirects = $derived(page.status === 404 && page.url.pathname !== '/');

	onMount(() => {
		if (redirects) {
			toast.error("We couldn't find that centre.");
			void goto('/', { replaceState: true });
		}
	});
</script>

{#if !redirects}
	<main class="p-4">
		<Page>
			<PageHeader
				title={page.status === 404 ? "We couldn't find that page" : 'Something went wrong'}
				description={page.error?.message}
			/>

			<Card border>
				<p class="text-sm text-(--text-muted)">
					Use the link your centre gave you, or try again in a moment.
				</p>

				{#if page.url.pathname !== '/'}
					<HyperTextLink href="/">Choose your centre</HyperTextLink>
				{/if}
			</Card>
		</Page>
	</main>
{/if}
