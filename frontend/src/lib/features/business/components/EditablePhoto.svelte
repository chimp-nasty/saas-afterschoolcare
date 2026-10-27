<!--
    One of the business's photo slots on a page (docs/public-site.md, stage
    9): the photo, or for its owner on desktop an "Add a photo" box, edited
    in place (EditableSection + PhotoForm). Holds no data and saves nothing:
    the page passes what to do with an upload, a removal and a description.
-->
<script lang="ts">
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import PhotoForm from './PhotoForm.svelte';
	import SitePhoto from './SitePhoto.svelte';

	import type { PhotoResponse } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';

	let {
		canEdit,
		kind,
		photo,
		emptyPrompt,
		onupload,
		onremove,
		onsavealt
	}: {
		canEdit: boolean;
		kind: 'hero_photo' | 'about_photo';
		photo: PhotoResponse | null;
		emptyPrompt: string;
		onupload: (file: File) => Promise<boolean>;
		onremove: () => Promise<void>;
		// Resolves once saved; the editor then closes.
		onsavealt: (alt: string | null) => Promise<ApiResponse<unknown>>;
	} = $props();
</script>

<EditableSection {canEdit} label="the photo" isEmpty={!photo} {emptyPrompt}>
	{#if photo}
		<SitePhoto {kind} {photo} />
	{/if}

	{#snippet editor(done)}
		<PhotoForm
			{kind}
			{photo}
			{onupload}
			{onremove}
			onsavealt={async (alt) => {
				const response = await onsavealt(alt);

				if (response.ok) done();

				return response;
			}}
			oncancel={done}
		/>
	{/snippet}
</EditableSection>
