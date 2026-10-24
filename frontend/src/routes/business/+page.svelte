<!--
    Business settings › Overview: what's set up and what isn't (business
    details, payments, each centre's services), and the way into each
    centre's own admin pages (Manage centre).
-->
<script lang="ts">
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import CentresTable from '$lib/features/business/components/CentresTable.svelte';
	import { manageCentre } from '$lib/features/business/manageCentre';

	let { data } = $props();

	const overview = $derived(data.overview);

	const noServices = $derived(overview?.locations.filter((location) => location.services_offered === 0) ?? []);
</script>

<Page width="wide">
	<PageHeader title={overview?.name ?? 'Business settings'} description="Your business's details, centres and payments." />

	{#if overview}
		<Card border>
			<div class="flex flex-col gap-4">
				<SectionHeading title="Setting up" />

				{#if overview.details_complete}
					<Notice tone="success">Your business details are filled in.</Notice>
				{:else}
					<Notice tone="warning">Add your legal name, ABN, email and phone.</Notice>
					<HyperTextLink href="/business/settings">Business details</HyperTextLink>
				{/if}

				{#if overview.takes_payments}
					<Notice tone="success">Payments are set up: families can book and pay.</Notice>
				{:else}
					<Notice tone="warning">
						{overview.payments_connected ? "Payments aren't ready yet, so families can't book." : "Connect Stripe so families can book and pay."}
					</Notice>
					<HyperTextLink href="/business/payments">Payments</HyperTextLink>
				{/if}

				{#if overview.locations.length === 0}
					<Notice tone="warning">Add your first centre.</Notice>
					<HyperTextLink href="/business/locations/new">Add a centre</HyperTextLink>
				{:else if noServices.length > 0}
					<Notice tone="warning">
						No services offered yet at {noServices.map((location) => location.name).join(', ')}. Set them up from Manage centre › Service settings.
					</Notice>
				{/if}
			</div>
		</Card>

		<Card border>
			<div class="flex flex-col gap-4">
				<SectionHeading title="Centres" />

				<CentresTable locations={overview.locations} onmanage={(location) => manageCentre(location.code)} />
			</div>
		</Card>
	{/if}
</Page>
