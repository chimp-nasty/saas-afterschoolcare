<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { RegistrationRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type RegistrationForm = Omit<RegistrationRequest, 'terms_accepted'> & {
		confirmPassword: string;
		terms_accepted: boolean;
	};

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<RegistrationRequest>;
	} = $props();

	const initialBody: RegistrationForm = {
		email: '',
		password: '',
		confirmPassword: '',
		first_name: '',
		last_name: '',
		terms_accepted: false
	};

	let body = $state<RegistrationForm>({ ...initialBody });
	let errors = $state<FormErrors<RegistrationForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		if (body.password !== body.confirmPassword) {
			errors.confirmPassword = 'Passwords do not match';
			return;
		}

		isLoading = true;

		try {
			// The checkbox is `required`, so it's always ticked by the time we get here.
			const response = await onsubmit({
				email: body.email,
				password: body.password,
				first_name: body.first_name,
				last_name: body.last_name,
				terms_accepted: true
			});

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
	{isLoading}
	handleSubmit={submit}
	submitLabel="Create account"
>
	<Field label="Email" error={errors.email}>
		{#snippet children(id)}
			<input {id} type="email" inputmode="email" autocomplete="username" maxlength="255" bind:value={body.email} required />
		{/snippet}
	</Field>

	<Field label="Password" error={errors.password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" minlength="8" maxlength="128" bind:value={body.password} required />
		{/snippet}
	</Field>

	<Field label="Confirm password" error={errors.confirmPassword}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="new-password" bind:value={body.confirmPassword} required />
		{/snippet}
	</Field>

	<Field label="First name" error={errors.first_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="given-name" maxlength="255" bind:value={body.first_name} required />
		{/snippet}
	</Field>

	<Field label="Last name" error={errors.last_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="family-name" maxlength="255" bind:value={body.last_name} required />
		{/snippet}
	</Field>

	<Field label="I accept the terms and conditions" error={errors.terms_accepted} inline>
		{#snippet children(id)}
			<input {id} type="checkbox" bind:checked={body.terms_accepted} required />
		{/snippet}
	</Field>
</Form>
