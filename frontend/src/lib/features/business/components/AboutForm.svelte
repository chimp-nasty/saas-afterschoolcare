<!--
    The business's about text (/about, previewed on the landing page),
    edited inline where it's shown (EditableSection). Sends only this field.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { SiteRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type AboutRequest = Pick<SiteRequest, 'about'>;

	let {
		initial,
		onsubmit,
		oncancel
	}: {
		initial: string | null;
		onsubmit: SubmitHandler<AboutRequest>;
		oncancel?: () => void;
	} = $props();

	// The saved text when the form opens; it then owns its edits.
	let about = $state(untrack(() => initial ?? ''));

	let errors = $state<FormErrors<AboutRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ about: about || null });

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save" {oncancel}>
	<Field label="About your business" error={errors.about}>
		{#snippet children(id)}
			<textarea {id} rows="8" maxlength="1000" bind:value={about}></textarea>
		{/snippet}
	</Field>
</Form>
