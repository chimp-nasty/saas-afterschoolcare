<!--
    Invite a business: the email its owner will register with. The page
    shows the one-time link to send them.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { CreateInviteRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<CreateInviteRequest>;
	} = $props();

	const empty: CreateInviteRequest = { email: '' };

	let body = $state<CreateInviteRequest>({ ...empty });
	let errors = $state<FormErrors<CreateInviteRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;

			if (response.ok) {
				body = { ...empty };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Create invite">
	<Field label="Owner's email" error={errors.email}>
		{#snippet children(id)}
			<input {id} type="email" inputmode="email" autocomplete="off" maxlength="255" bind:value={body.email} required />
		{/snippet}
	</Field>
</Form>
