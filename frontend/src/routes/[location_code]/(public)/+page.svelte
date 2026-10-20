<!--
    The location's landing page, before login: what it offers (times, ages,
    prices, policies), where it is, and how to get started.
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';
	import ServiceCard from '$lib/features/services/components/ServiceCard.svelte';

	import { auth } from '$lib/auth/state.svelte';
	import { logout } from '$lib/auth/logout';

	let { data } = $props();

	const name = $derived(data.location.display_name ?? data.location.location_name);
</script>

<Page>
	<PageHeader
		title={`Welcome to ${name}`}
		description="See what we offer, then book and pay online."
	/>

	{#if data.signedInElsewhere}
		<!-- Logged in at another of the tenant's centres; that session
		     doesn't count here (routes/[location_code]/+layout.ts). -->
		<Card border>
			<p class="text-sm text-(--text-muted)">
				You're logged in at {data.signedInElsewhere.locationName}. Log out to
				use this centre instead.
			</p>
		</Card>

		<ActionBar>
			<Button variant="ghost" onclick={() => logout(data.locationCode)}>
				Log out
			</Button>

			<Button onclick={() => goto(`/${data.signedInElsewhere?.locationCode}/home`)}>
				Go to {data.signedInElsewhere.locationName}
			</Button>
		</ActionBar>
	{:else if $auth.authenticated}
		<Button fullWidth onclick={() => goto(`/${data.locationCode}/home`)}>
			Go to your bookings
		</Button>
	{:else}
		<ActionBar>
			<Button variant="ghost" onclick={() => goto(`/${data.locationCode}/register`)}>
				Create an account
			</Button>

			<Button onclick={() => goto(`/${data.locationCode}/login`)}>
				Log in
			</Button>
		</ActionBar>
	{/if}

	<section class="flex flex-col gap-4">
		<h2 class="text-lg font-extrabold text-(--text)">
			Our services
		</h2>

		{#each data.services as service (service.id)}
			<ServiceCard {service} />
		{:else}
			<Card border>
				<p class="text-sm text-(--text-muted)">
					Services will be listed here soon.
				</p>
			</Card>
		{/each}
	</section>

	<CentreCard location={data.location} />
</Page>
