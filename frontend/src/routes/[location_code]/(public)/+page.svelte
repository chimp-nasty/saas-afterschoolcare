<!--
    The location's landing page, before login: what it offers (times, ages,
    prices, policies), where it is, and how to get started.
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
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
		<Notice>
			You're logged in at {data.signedInElsewhere.locationName}. Log out to
			use this centre instead.
		</Notice>

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
		<SectionHeading title="Our services" />

		{#each data.services as service (service.id)}
			<ServiceCard {service} />
		{:else}
			<EmptyState message="Services will be listed here soon." />
		{/each}
	</section>

	<CentreCard location={data.location} />
</Page>
