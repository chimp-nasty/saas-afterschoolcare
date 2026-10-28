<!--
    Two of the platform's landing page words edited inline where they're
    shown (EditableSection): a title and the text under it, for the hero
    (headline, hero_text) or the about band (about_title, about). Sends only
    those two fields.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { PlatformSiteRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type TitleField = 'headline' | 'about_title';
	type TextField = 'hero_text' | 'about';

	let {
		fields,
		labels,
		initial,
		textMax,
		onsubmit,
		oncancel
	}: {
		fields: [TitleField, TextField];
		labels: [string, string];
		initial: [string | null, string | null];
		textMax: number;
		onsubmit: SubmitHandler<PlatformSiteRequest>;
		oncancel?: () => void;
	} = $props();

	// The saved values when the form opens; it then owns its edits.
	let title = $state(untrack(() => initial[0] ?? ''));
	let text = $state(untrack(() => initial[1] ?? ''));

	let errors = $state<FormErrors<PlatformSiteRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ [fields[0]]: title || null, [fields[1]]: text || null });

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save" {oncancel}>
	<Field label={labels[0]} error={errors[fields[0]]}>
		{#snippet children(id)}
			<input {id} type="text" maxlength="120" bind:value={title} />
		{/snippet}
	</Field>

	<Field label={labels[1]} error={errors[fields[1]]}>
		{#snippet children(id)}
			<textarea {id} rows="5" maxlength={textMax} bind:value={text}></textarea>
		{/snippet}
	</Field>
</Form>
