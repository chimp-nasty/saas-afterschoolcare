<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { LoginRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<LoginRequest>;
	} = $props();

	const initialBody: LoginRequest = {
		email: '',
		password: ''
	};

	let body = $state<LoginRequest>({ ...initialBody });
	let errors = $state<FormErrors<LoginRequest>>({});
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
	{isLoading}
	handleSubmit={submit}
	submitLabel="Log in"
>
	<Field label="Email" error={errors.email}>
		{#snippet children(id)}
			<input {id} type="email" inputmode="email" autocomplete="username" maxlength="255" bind:value={body.email} required />
		{/snippet}
	</Field>

	<Field label="Password" error={errors.password}>
		{#snippet children(id)}
			<input {id} type="password" autocomplete="current-password" bind:value={body.password} required />
		{/snippet}
	</Field>
</Form>
