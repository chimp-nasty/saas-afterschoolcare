<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';

	import {
		loginRequestSchema,
		type LoginRequest
	} from '$lib/api/auth/types/types';

	import type { FormErrors } from '$lib/types/forms';
	import { createFormState, validateForm } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (body: LoginRequest) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	const initialBody: LoginRequest = {
		email: '',
		password: ''
	};

	let body = $state<LoginRequest>(
		createFormState(initialBody)
	);

	let errors = $state<FormErrors<LoginRequest>>({});

	async function submit() {
		const validation = validateForm(loginRequestSchema, body);
		errors = validation.errors;

		if (!validation.valid) return;
		await handleSubmit(body);
	}

	export function reset() {
		body = createFormState(initialBody);
		errors = {};
	}
</script>

<Form
	{isLoading}
	handleSubmit={submit}
>
	<EmailInput
		bind:value={body.email}
		label="Email"
		error={errors.email}
	/>

	<PasswordInput
		bind:value={body.password}
		label="Password"
		error={errors.password}
	/>
</Form>