<!--
    Ask the family for documentation. The message is shown to the family on
    the child's page and in their actions, so it should say exactly what's
    needed.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type DocumentationRequest = {
		message: string;
	};

	let {
		firstName,
		onsubmit
	}: {
		firstName: string;
		onsubmit: SubmitHandler<DocumentationRequest>;
	} = $props();

	let body = $state<DocumentationRequest>({ message: '' });
	let errors = $state<FormErrors<DocumentationRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit(body);

			errors = response.fieldErrors;

			if (response.ok) {
				body = { message: '' };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form
	{isLoading}
	handleSubmit={submit}
	submitLabel="Request documents"
>
	<Field label="What the family needs to provide" error={errors.message}>
		{#snippet children(id)}
			<textarea
				{id}
				rows="4"
				maxlength="1000"
				placeholder={`e.g. Please upload ${firstName}'s signed asthma action plan.`}
				bind:value={body.message}
				required
			></textarea>
		{/snippet}
	</Field>

	<p class="text-sm text-(--text-muted)">
		The family sees this message and is asked to upload documents.
		{firstName} can't be booked until you approve.
	</p>
</Form>
