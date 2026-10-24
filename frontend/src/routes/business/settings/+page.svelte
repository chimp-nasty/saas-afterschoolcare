<!--
    Business settings › Business details: what families and your landing
    page show about the business.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';

	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import BusinessSettingsForm from '$lib/features/business/components/BusinessSettingsForm.svelte';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import type { BusinessSettingsRequest } from '$lib/api/schema';

	let { data } = $props();

	const businessApi = createBusinessApi();

	const initial = $derived.by((): BusinessSettingsRequest | null => {
		const settings = data.settings;

		if (!settings) return null;

		return {
			name: settings.name,
			legal_name: settings.legal_name,
			abn: settings.abn,
			email: settings.email,
			phone: settings.phone,
			about: settings.about
		};
	});

	async function save(body: BusinessSettingsRequest) {
		const response = await businessApi.updateSettings(body);

		if (response.ok) {
			await invalidate('app:business');
		}

		return response;
	}
</script>

<Page>
	<PageHeader title="Business details" description="Shown to families on your site." />

	{#if initial}
		<BusinessSettingsForm {initial} onsubmit={save} />
	{/if}
</Page>
