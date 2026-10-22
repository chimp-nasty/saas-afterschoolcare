<!--
    Reopen an approved child for review: they go back to Waiting, and new
    bookings wait until an admin approves them again. The family always
    gets a message in their account (no email): the one written here, or,
    left blank, one saying staff are reviewing.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type ReopenRequest = {
		message: string;
	};

	let {
		firstName,
		onsubmit
	}: {
		firstName: string;
		onsubmit: SubmitHandler<ReopenRequest>;
	} = $props();

	let body = $state<ReopenRequest>({ message: '' });
	let errors = $state<FormErrors<ReopenRequest>>({});
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

<Form {isLoading} handleSubmit={submit} submitLabel="Reopen for review">
	<Field label="Message to the family (optional)" error={errors.message}>
		{#snippet children(id)}
			<textarea
				{id}
				rows="3"
				maxlength="1000"
				placeholder={`Our staff are reviewing ${firstName}'s medical details. Until the review is done, new bookings for ${firstName} will wait. Existing bookings aren't affected.`}
				bind:value={body.message}
			></textarea>
		{/snippet}
	</Field>

	<p class="text-sm text-(--text-muted)">
		{firstName} goes back to Waiting for review. The family gets this message in their account; left blank, they
		get the one shown.
	</p>
</Form>
