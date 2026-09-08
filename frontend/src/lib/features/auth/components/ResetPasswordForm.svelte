<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';

	import {
		resetPasswordFormSchema,
		type ResetPasswordForm
	} from '$lib/features/auth/types';

	import type { FormErrors } from '$lib/types/forms';
	import { createFormState, validateForm } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (password: string) => void | Promise<void>;
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

	async function submit() {
		const validation = validateForm(resetPasswordFormSchema, body);
		errors = validation.errors;

		if (!validation.valid) return;
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