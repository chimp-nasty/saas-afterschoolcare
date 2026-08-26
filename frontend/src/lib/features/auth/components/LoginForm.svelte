<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';

	import type { LoginRequest } from '$lib/api/auth/types/types';
	import type { FormErrors } from '$lib/types/forms';
	import { createFormState } from '$lib/utils/forms';

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

	function validate(): boolean {
		errors = {};

		if (!body.email.trim()) {
			errors.email = 'Email is required';
		}

		if (!body.password) {
			errors.password = 'Password is required';
		}

		return Object.keys(errors).length === 0;
	}

	async function submit() {
		if (!validate()) {
			return;
		}

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