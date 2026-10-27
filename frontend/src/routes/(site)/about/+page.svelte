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
	import EditablePhoto from '$lib/features/business/components/EditablePhoto.svelte';
	import { uploadSiteFile } from '$lib/features/business/siteFiles';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { SiteRequest } from '$lib/api/schema';

	let { data } = $props();

	const businessApi = createBusinessApi();

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Us');

	const hasContact = $derived(Boolean(business?.email || business?.phone));

	// The about photo (stage 9): an upload or removal takes effect at once.
	async function uploadPhoto(file: File) {
		const ok = await uploadSiteFile(businessApi, 'about_photo', file);

		if (ok) await invalidate('app:business-site');

		return ok;
	}

	async function removePhoto() {
		const response = await businessApi.removeImage('about_photo');

		if (response.ok) await invalidate('app:business-site');
	}

	async function savePhotoAlt(alt: string | null) {
		const response = await businessApi.updateSite({ about_photo_alt: alt });

		if (response.ok) await invalidate('app:business-site');

		return response;
	}

	// Room for the photo when there is one, or its owner may add one.
	const photoColumn = $derived(Boolean(business?.about_photo) || data.isOwner);

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
	<div class={['grid gap-10 lg:items-center', photoColumn && 'lg:grid-cols-2']}>
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
					<p class="pr-14 text-base whitespace-pre-line text-(--text) md:text-lg">
						{business.about}
					</p>
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

		{#if photoColumn}
			<div class={[!business?.about_photo && 'hidden md:block']}>
				<EditablePhoto
					canEdit={data.isOwner}
					src={business?.about_photo ? siteFileUrl('about_photo', business.about_photo.version) : null}
					photo={business?.about_photo ?? null}
					emptyPrompt="Add a photo beside your about text"
					onupload={uploadPhoto}
					onremove={removePhoto}
					onsavealt={savePhotoAlt}
				/>
			</div>
		{/if}
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
