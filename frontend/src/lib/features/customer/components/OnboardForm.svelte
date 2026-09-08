<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';
    import TextInput from '$lib/components/forms/fields/TextInput.svelte';
    import CheckboxInput from '$lib/components/forms/fields/CheckboxInput.svelte';

	import { 
		registrationFormSchema,
		type RegistrationForm
	} from '$lib/features/customer/types';
	import type { FormErrors } from '$lib/types/forms';
	import { createFormState, validateForm } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (body: RegistrationForm) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	const initialBody: RegistrationForm = {
		email: '',
		password: '',
		confirmPassword: '',
        first_name: '',
        last_name: '',
        terms_accepted: false,
	};

	let body = $state<RegistrationForm>(
		createFormState(initialBody)
	);

	let errors = $state<FormErrors<RegistrationForm>>({});

	async function submit() {
		const validation = validateForm(registrationFormSchema, body);
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

	<PasswordInput
		bind:value={body.confirmPassword}
		label="Confirm Password"
		error={errors.confirmPassword}
	/>

    <TextInput
        bind:value={body.first_name}
        label="First Name"
        error={errors.first_name}
    />

    <TextInput
        bind:value={body.last_name}
        label="Last Name"
        error={errors.last_name}
    />

    <CheckboxInput
        bind:value={body.terms_accepted}
        label="Accept Terms and Conditions"
        error={errors.terms_accepted}
    />
</Form>