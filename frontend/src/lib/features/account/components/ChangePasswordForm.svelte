<!--
    Change your password: the current one (to confirm it's you), then the
    new one twice. The match check is the only one here; the server checks
    the current password and the new one's length.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { ChangePasswordRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type ChangePasswordForm = {
		current_password: string;
		new_password: string;
		confirm_password: string;
	};

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<ChangePasswordRequest>;
	} = $props();

	const empty: ChangePasswordForm = { current_password: '', new_password: '', confirm_password: '' };

	let body = $state<ChangePasswordForm>({ ...empty });
	let errors = $state<FormErrors<ChangePasswordForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		if (body.new_password !== body.confirm_password) {
			errors = { confirm_password: "The passwords don't match." };
			return;
		}

		isLoading = true;

		try {
			const response = await onsubmit({
				current_password: body.current_password,
				new_password: body.new_password
			});

			errors = response.fieldErrors;

			if (response.ok) {
				body = { ...empty };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Change password">
	<Field label="Current password" error={errors.current_password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="current-password" bind:value={body.current_password} required />
		{/snippet}
	</Field>

	<Field label="New password (at least 8 characters)" error={errors.new_password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" minlength="8" maxlength="128" bind:value={body.new_password} required />
		{/snippet}
	</Field>

	<Field label="New password again" error={errors.confirm_password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" minlength="8" maxlength="128" bind:value={body.confirm_password} required />
		{/snippet}
	</Field>
</Form>
