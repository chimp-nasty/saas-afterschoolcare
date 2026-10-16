<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type ResetPasswordForm = {
		password: string;
		confirmPassword: string;
	};

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<string>;
	} = $props();

	const initialBody: ResetPasswordForm = {
		password: '',
		confirmPassword: ''
	};

	let body = $state<ResetPasswordForm>({ ...initialBody });
	let errors = $state<FormErrors<ResetPasswordForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		if (body.password !== body.confirmPassword) {
			errors.confirmPassword = 'Passwords do not match';
			return;
		}

		isLoading = true;

		try {
			const response = await onsubmit(body.password);

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
	submitLabel="Reset password"
>
	<Field label="New password" error={errors.password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" minlength="8" maxlength="128" bind:value={body.password} required />
		{/snippet}
	</Field>

	<Field label="Confirm password" error={errors.confirmPassword}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" bind:value={body.confirmPassword} required />
		{/snippet}
	</Field>
</Form>
