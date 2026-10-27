<!--
    /about (docs/public-site.md): the business's about text, which its owner
    edits here on desktop (EditableSection; section 6), and how to reach it
    (Business settings › Business details). A fuller page (photos,
    sections) may come later.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';

	import Card from '$lib/components/layout/Card.svelte';
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import SiteSection from '$lib/components/layout/SiteSection.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import SiteHeading from '$lib/components/text/SiteHeading.svelte';
	import AboutForm from '$lib/features/business/components/AboutForm.svelte';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import type { SiteRequest } from '$lib/api/schema';

	let { data } = $props();

	const businessApi = createBusinessApi();

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Us');

	const hasContact = $derived(Boolean(business?.email || business?.phone));

	async function saveAbout(body: Pick<SiteRequest, 'about'>, done: () => void) {
		const response = await businessApi.updateSite(body);

		if (response.ok) {
			await invalidate('app:business-site');
			done();
		}

		return response;
	}
</script>

<SiteSection>
	<div class="flex max-w-3xl flex-col gap-5 py-4 md:py-8">
		<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>

		<p class="label-text">About</p>

		<h1 class="display-text">{name}</h1>

		<!-- Visitors see "soon" when there's nothing yet; the owner sees the
		     prompt to write it. -->
		<EditableSection
			canEdit={data.isOwner}
			label="your about text"
			isEmpty={data.isOwner && !business?.about}
			emptyPrompt="Add a few words about your business"
		>
			{#if business?.about}
				<p class="whitespace-pre-line pr-14 text-base text-(--text) md:text-lg">{business.about}</p>
			{:else}
				<EmptyState message="More about us soon." />
			{/if}

			{#snippet editor(done)}
				<AboutForm
					initial={business?.about ?? null}
					onsubmit={(body) => saveAbout(body, done)}
					oncancel={done}
				/>
			{/snippet}
		</EditableSection>
	</div>
</SiteSection>

{#if business && hasContact}
	<SiteSection tone="muted">
		<SiteHeading title="Contact" description="Each centre's address and phone are on its page." />

		<div class="max-w-xl">
			<Card border>
				<LabelValueList
					items={[
						{ label: 'Email', value: business.email },
						{ label: 'Phone', value: business.phone }
					]}
				/>
			</Card>
		</div>
	</SiteSection>
{/if}
