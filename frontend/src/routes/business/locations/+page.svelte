<!--
    Business settings › Centres: every centre of the business, to add, edit
    or open (Manage centre switches the login into it).
-->
<script lang="ts">
	import { goto } from '$app/navigation';

	import Button from '$lib/components/actions/Button.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import CentresTable from '$lib/features/business/components/CentresTable.svelte';
	import { manageCentre } from '$lib/features/business/manageCentre';

	let { data } = $props();
</script>

<Page width="wide">
	<PageHeader
		title="Centres"
		description="A new centre offers no services until you set them up in Manage centre › Service settings."
	>
		{#snippet actions()}
			<Button onclick={() => goto('/business/locations/new')}>Add a centre</Button>
		{/snippet}
	</PageHeader>

	<CentresTable
		locations={data.locations}
		onmanage={(location) => manageCentre(location.code)}
		onedit={(location) => goto(`/business/locations/${location.id}`)}
	/>
</Page>
