<!--
    Platform › Enquiries (docs/platform-site.md): messages from the
    platform's contact page. Each was also emailed to the contact address
    with Reply-To the person, so they're answered from that mailbox; close
    one here once it's dealt with.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';

	import TabbedPanels from '$lib/components/controls/TabbedPanels.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import PlatformEnquiryList from '$lib/features/platform/components/PlatformEnquiryList.svelte';

	import { createPlatformEnquiriesApi } from '$lib/api/platform/adapters/platformEnquiries';
	import type { PlatformEnquiryResponse } from '$lib/api/schema';
	import { enquiryTabs } from '$lib/navigation/tabs';

	let { data } = $props();

	const enquiriesApi = createPlatformEnquiriesApi();

	let activeTab = $state<string>(enquiryTabs.OPEN);

	const tabs = $derived([
		{ id: enquiryTabs.OPEN, label: `Open (${data.open.length})` },
		{ id: enquiryTabs.CLOSED, label: `Closed (${data.closed.length})` }
	]);

	async function toggle(enquiry: PlatformEnquiryResponse) {
		const response = enquiry.closed_at ? await enquiriesApi.reopen(enquiry.id) : await enquiriesApi.close(enquiry.id);

		if (response.ok) await invalidate('app:platform-enquiries');
	}
</script>

<Page width="wide">
	<PageHeader
		title="Enquiries"
		description="Messages from the platform's contact page, newest first. Each one is also emailed to the contact address: reply from there."
	/>

	<TabbedPanels {tabs} initialTab={enquiryTabs.OPEN} bind:activeTab queryParam="state">
		{#snippet panel(id)}
			{#if id === enquiryTabs.OPEN}
				<PlatformEnquiryList enquiries={data.open} empty="No open enquiries." ontoggle={toggle} />
			{:else}
				<PlatformEnquiryList enquiries={data.closed} empty="No closed enquiries." ontoggle={toggle} />
			{/if}
		{/snippet}
	</TabbedPanels>
</Page>
