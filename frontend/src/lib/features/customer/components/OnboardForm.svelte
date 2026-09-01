<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';
    import TextInput from '$lib/components/forms/fields/TextInput.svelte';
    import CheckboxInput from '$lib/components/forms/fields/CheckboxInput.svelte';

	import type { RegistrationRequest } from '$lib/api/auth/types/types';
	import type { FormErrors } from '$lib/types/forms';
	import { createFormState } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (body: RegistrationRequest) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	const initialBody: RegistrationRequest = {
		email: '',
		password: '',
        first_name: '',
        last_name: '',
        terms_accepted: false,
	};

    let confirmPassword = $state('');

	let body = $state<RegistrationRequest>(
		createFormState(initialBody)
	);

	let errors = $state<FormErrors<RegistrationRequest>>({});

	function validate(): boolean {
		errors = {};

		if (!body.email.trim()) {
			errors.email = 'Email is required';
		}

		if (!body.password) {
			errors.password = 'Password is required';
		}

        if (confirmPassword !== body.password) {
            errors.password = 'Passwords do not match';
        }

        if (!body.first_name) {
            errors.first_name = 'First name is required';
        }

        if (!body.last_name) {
            errors.last_name = 'Last name is required';
        }

        if (body.terms_accepted === false) {
            errors.terms_accepted = 'You must accept terms to continue';
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
        confirmPassword = '';
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
		bind:value={confirmPassword}
		label="Confirm Password"
		error={errors.password}
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