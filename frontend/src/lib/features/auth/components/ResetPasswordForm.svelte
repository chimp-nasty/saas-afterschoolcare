<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';

	import type { FormErrors } from '$lib/types/forms';
	import { createFormState } from '$lib/utils/forms';

	type ResetPasswordForm = {
		password: string;
		confirmPassword: string;
	};

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (
			password: string
		) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	const initialBody: ResetPasswordForm = {
		password: '',
		confirmPassword: ''
	};

	let body = $state<ResetPasswordForm>(
		createFormState(initialBody)
	);

	let errors = $state<FormErrors<ResetPasswordForm>>({});

	function validate(): boolean {
		errors = {};

		if (!body.password) {
			errors.password = 'Password is required';
		}

		if (!body.confirmPassword) {
			errors.confirmPassword = 'Confirm your password';
		}

		if (
			body.password &&
			body.confirmPassword &&
			body.password !== body.confirmPassword
		) {
			errors.confirmPassword = 'Passwords do not match';
		}

		return Object.keys(errors).length === 0;
	}

	async function submit() {
		if (!validate()) {
			return;
		}

		await handleSubmit(body.password);
	}

	export function reset() {
		body = createFormState(initialBody);
		errors = {};
	}
</script>

<Form
	handleSubmit={submit}
	{isLoading}
	submitLabel="Reset password"
>
	<PasswordInput
		bind:value={body.password}
		label="New password"
		error={errors.password}
	/>

	<PasswordInput
		bind:value={body.confirmPassword}
		label="Confirm password"
		error={errors.confirmPassword}
	/>
</Form>