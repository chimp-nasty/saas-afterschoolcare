<!--
    The location's landing page, before login: what it offers (times, ages,
    prices, policies), where it is, and how to get started. Laid out as the
    public site's bands (docs/public-site.md); stage 6 rebuilds it as the
    full centre page.
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import CentreCard from '$lib/features/location/components/CentreCard.svelte';
	import ServiceCard from '$lib/features/services/components/ServiceCard.svelte';

	import { auth } from '$lib/auth/state.svelte';
	import { logout } from '$lib/auth/logout';

	let { data } = $props();

	const name = $derived(data.location.location_name);
</script>

<SiteSection>
	<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
		<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

		<p class="label-text">Your centre</p>

		<h1 class="display-text">{name}</h1>

		<p class="text-base text-(--text-muted) md:text-lg">
			See what we offer, then book and pay online.
		</p>

		{#if data.signedInElsewhere}
			<!-- Logged in at another of the tenant's centres; that session
			     doesn't count here (routes/[location_code]/+layout.ts). -->
			<Notice>
				You're logged in at {data.signedInElsewhere.locationName}. Log out to
				use this centre instead.
			</Notice>

			<ActionBar start>
				<Button variant="ghost" onclick={() => logout(data.locationCode)}>
					Log out
				</Button>

				<Button onclick={() => goto(`/${data.signedInElsewhere?.locationCode}/home`)}>
					Go to {data.signedInElsewhere.locationName}
				</Button>
			</ActionBar>
		{:else if $auth.authenticated}
			<ActionBar start>
				<Button onclick={() => goto(`/${data.locationCode}/home`)}>
					Go to your bookings
				</Button>
			</ActionBar>
		{:else}
			<ActionBar start>
				<Button variant="ghost" onclick={() => goto(`/${data.locationCode}/login`)}>
					Log in
				</Button>

				<Button onclick={() => goto(`/${data.locationCode}/register`)}>
					Enrol now
				</Button>
			</ActionBar>
		{/if}
	</div>
</SiteSection>

<SiteSection id="services" tone="muted">
	<SiteHeading title="Our services" />

	{#if data.services.length > 0}
		<div class="grid gap-4 md:grid-cols-2">
			{#each data.services as service (service.id)}
				<ServiceCard {service} />
			{/each}
		</div>
	{:else}
		<EmptyState message="Services will be listed here soon." />
	{/if}
</SiteSection>

<SiteSection>
	<SiteHeading title="Find us" />

	<div class="max-w-xl">
		<CentreCard location={data.location} />
	</div>
</SiteSection>
