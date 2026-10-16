<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { ForgotPasswordRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<ForgotPasswordRequest>;
	} = $props();

	const initialBody: ForgotPasswordRequest = {
		email: ''
	};

	let body = $state<ForgotPasswordRequest>({ ...initialBody });
	let errors = $state<FormErrors<ForgotPasswordRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit(body);

			errors = response.fieldErrors;

			if (response.ok) {
				body = { ...initialBody };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form
	handleSubmit={submit}
	{isLoading}
	submitLabel="Send reset link"
>
	<Field label="Email" error={errors.email}>
		{#snippet children(id)}
			<input {id} type="email" inputmode="email" autocomplete="username" maxlength="255" bind:value={body.email} required />
		{/snippet}
	</Field>
</Form>
