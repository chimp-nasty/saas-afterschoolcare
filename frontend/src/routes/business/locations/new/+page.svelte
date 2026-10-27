<!--
    Business settings › Add a centre. It starts with every service, none
    offered to families yet, and you as its superadmin.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import { goto, invalidate } from '$app/navigation';

	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import LocationForm from '$lib/features/business/components/LocationForm.svelte';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import type { BusinessLocationRequest } from '$lib/api/schema';

	const businessApi = createBusinessApi();

	async function add(body: BusinessLocationRequest) {
		const response = await businessApi.createLocation(body);

		if (response.ok) {
			await invalidate('app:business');
			await goto('/business/locations');
		}

		return response;
	}
</script>

<Page>
	<PageHeader title="Add a centre" description="Families find it on your site's home page. It takes bookings once its services are set up and payments are on." />

	<LocationForm submitLabel="Add centre" onsubmit={add} />

	<ActionBar start>
		<Button variant="ghost" onclick={() => goto('/business/locations')}>Back to centres</Button>
	</ActionBar>
</Page>
