<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';

	import { 
		forgotPasswordRequestSchema,
		type ForgotPasswordRequest
	} from '$lib/api/auth/types/types';
	import type { FormErrors } from '$lib/types/forms';
	import { createFormState, validateForm } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (
			body: ForgotPasswordRequest
		) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	const initialBody: ForgotPasswordRequest = {
		email: ''
	};

	let body = $state<ForgotPasswordRequest>(
		createFormState(initialBody)
	);

	let errors = $state<FormErrors<ForgotPasswordRequest>>({});

	async function submit() {
		const validation = validateForm(forgotPasswordRequestSchema, body);
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
	handleSubmit={submit}
	{isLoading}
	submitLabel="Send reset link"
>
	<EmailInput
		bind:value={body.email}
		label="Email"
		error={errors.email}
	/>
</Form>