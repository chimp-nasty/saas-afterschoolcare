<!--
    A photo slot on the public site (docs/public-site.md, stage 9): the
    photo (or `fallback`, another shown in its place), or for whoever may
    edit it on desktop an "Add a photo" box, edited in place
    (EditableSection + PhotoForm). Holds no data and saves nothing: the page
    passes the photo's link and what to do with an upload, a removal and a
    description.
-->
<script lang="ts">
	import EditableSection from '$lib/components/layout/EditableSection.svelte';
	import PhotoForm from './PhotoForm.svelte';
	import SitePhoto from './SitePhoto.svelte';

	import type { PhotoResponse } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';

	let {
		canEdit,
		photo,
		src,
		fallback = null,
		emptyPrompt,
		onupload,
		onremove,
		onsavealt,
		shape = 'rounded'
	}: {
		canEdit: boolean;
		photo: PhotoResponse | null;
		// The photo's link (with its version), when there is one.
		src: string | null;
		// Shown when there's no photo of its own (a centre: the business's).
		fallback?: { src: string; alt: string | null; note: string } | null;
		emptyPrompt: string;
		onupload: (file: File) => Promise<boolean>;
		onremove: () => Promise<void>;
		// Resolves once saved; the editor then closes.
		onsavealt: (alt: string | null) => Promise<ApiResponse<unknown>>;
		// How the photo is cut (SitePhoto).
		shape?: 'rounded' | 'wave';
	} = $props();

	const shown = $derived(photo && src ? { src, alt: photo.alt } : fallback);
</script>

<EditableSection {canEdit} label="the photo" isEmpty={!shown} {emptyPrompt}>
	{#if shown}
		<SitePhoto src={shown.src} alt={shown.alt} {shape} />
	{/if}

	{#snippet editor(done)}
		<PhotoForm
			{photo}
			{src}
			fallbackNote={fallback?.note}
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
