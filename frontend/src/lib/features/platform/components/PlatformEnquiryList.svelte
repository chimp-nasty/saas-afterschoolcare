<!--
    Platform › Enquiries: each message in full (they're read here, and
    answered from the contact mailbox the notice email went to), with
    Close or Reopen.
-->
<script lang="ts">
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { PlatformEnquiryResponse } from '$lib/api/schema';
	import { PLATFORM_ENQUIRY_TOPICS } from '$lib/features/platform/enquiries';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		enquiries,
		empty,
		ontoggle
	}: {
		enquiries: PlatformEnquiryResponse[];
		empty: string;
		// Closes an open one, reopens a closed one.
		ontoggle: (enquiry: PlatformEnquiryResponse) => Promise<void>;
	} = $props();

	let busyId = $state<string | null>(null);

	async function toggle(enquiry: PlatformEnquiryResponse) {
		busyId = enquiry.id;

		try {
			await ontoggle(enquiry);
		} finally {
			busyId = null;
		}
	}
</script>

{#if enquiries.length === 0}
	<EmptyState message={empty} />
{:else}
	<div class="flex flex-col gap-4">
		{#each enquiries as enquiry (enquiry.id)}
			{#snippet email()}
				<HyperTextLink inline href={`mailto:${enquiry.email}`}>{enquiry.email}</HyperTextLink>
			{/snippet}

			<Card border>
				<div class="flex flex-col gap-4">
					<SectionHeading title={enquiry.name} description={PLATFORM_ENQUIRY_TOPICS[enquiry.topic]} />

					<LabelValueList
						items={[
							{ label: 'Sent', value: formatTimestamp(enquiry.created_at) },
							{ label: 'Email', content: email },
							{ label: 'Business', value: enquiry.business_name },
							{ label: 'Phone', value: enquiry.phone }
						]}
					/>

					<p class="whitespace-pre-line text-base text-(--text)">{enquiry.message}</p>

					<ActionBar start>
						<Button variant="ghost" width="w-32" isLoading={busyId === enquiry.id} onclick={() => toggle(enquiry)}>
							{enquiry.closed_at ? 'Reopen' : 'Close'}
						</Button>
					</ActionBar>
				</div>
			</Card>
		{/each}
	</div>
{/if}
