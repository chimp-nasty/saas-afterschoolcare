<!--
    One of the business's photos, edited inline where it's shown
    (EditablePhoto): upload a new one or remove it (straight away), and its
    description for screen readers (saved with Save). Photos are re-saved
    for the web without their metadata, so where they were taken isn't
    published.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SiteFileUpload from './SiteFileUpload.svelte';
	import SitePhoto from './SitePhoto.svelte';

	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import type { PhotoResponse } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';
	import { SITE_FILE_ACCEPT } from '../siteFiles';

	let {
		kind,
		photo,
		onupload,
		onremove,
		onsavealt,
		oncancel
	}: {
		kind: 'hero_photo' | 'about_photo';
		photo: PhotoResponse | null;
		onupload: (file: File) => Promise<boolean>;
		onremove: () => Promise<void>;
		onsavealt: (alt: string | null) => Promise<ApiResponse<unknown>>;
		oncancel?: () => void;
	} = $props();

	// The saved description when the form opens; it then owns its edits.
	let alt = $state(untrack(() => photo?.alt ?? ''));
	let isLoading = $state(false);

	async function submit() {
		isLoading = true;

		try {
			await onsavealt(alt || null);
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save" {oncancel}>
	{#if photo}
		<div class="max-w-md">
			<SitePhoto {kind} {photo} />
		</div>
	{/if}

	<SiteFileUpload
		title="Photo"
		description="PNG, JPEG or WebP, up to 8 MB. Saved for the web, without the details cameras add (such as where it was taken)."
		accept={SITE_FILE_ACCEPT[kind].join(',')}
		status={photo ? 'This photo is on your site.' : 'No photo yet.'}
		viewHref={photo ? siteFileUrl(kind, photo.version) : null}
		{onupload}
		{onremove}
	/>

	<Notice tone="warning"
		>Only use photos of children whose families have agreed to them being on your website.</Notice
	>

	{#if photo}
		<Field label="Description, for people using screen readers (optional)">
			{#snippet children(id)}
				<input
					{id}
					type="text"
					maxlength="200"
					placeholder="e.g. Students playing basketball on the oval"
					bind:value={alt}
				/>
			{/snippet}
		</Field>
	{/if}
</Form>
