<!--
    Upload one document for a child: what it is, and the file (a PDF, or a
    photo of a paper plan). The page does the upload and reports progress;
    the server checks the file's type and size.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import { childDocumentTypeValues, type ChildDocumentType } from '$lib/api/schema';
	import { DOCUMENT_ACCEPT, DOCUMENT_TYPE_LABELS } from '$lib/features/children/documents';
	import type { ChildDocumentUpload } from '$lib/features/children/types';
	import type { SubmitHandler } from '$lib/types/forms';

	let {
		progress = null,
		onsubmit
	}: {
		// Percent of the file sent so far, while uploading.
		progress?: number | null;
		onsubmit: SubmitHandler<ChildDocumentUpload>;
	} = $props();

	let documentType = $state<ChildDocumentType | ''>('');
	let files = $state<FileList | undefined>();
	let fileInput = $state<HTMLInputElement>();

	let errors = $state<{ document_type?: string; file?: string }>({});
	let isLoading = $state(false);

	async function submit() {
		const file = files?.[0];

		if (!documentType || !file) return;

		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ document_type: documentType, file });

			errors = {
				document_type: response.fieldErrors.document_type,
				file:
					response.fieldErrors.filename ??
					response.fieldErrors.content_type ??
					response.fieldErrors.size_bytes
			};

			if (response.ok) {
				documentType = '';
				files = undefined;

				if (fileInput) fileInput.value = '';
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form
	{isLoading}
	handleSubmit={submit}
	submitLabel="Upload"
>
	<Field label="Document" error={errors.document_type}>
		{#snippet children(id)}
			<Select
				{id}
				bind:value={documentType}
				required
				placeholder="Document type"
				options={childDocumentTypeValues.map((value) => ({ value, label: DOCUMENT_TYPE_LABELS[value] }))}
			/>
		{/snippet}
	</Field>

	<Field label="File" error={errors.file}>
		{#snippet children(id)}
			<input
				{id}
				type="file"
				accept={DOCUMENT_ACCEPT}
				bind:files
				bind:this={fileInput}
				required
			/>
		{/snippet}
	</Field>

	<p class="text-sm text-(--text-muted)">
		A PDF, or a clear photo of each page (JPEG, PNG or HEIC), up to 10 MB.
	</p>

	{#if isLoading && progress !== null}
		<p class="text-sm text-(--text-muted)" aria-live="polite">
			Uploading… {progress}%
		</p>
	{/if}
</Form>
