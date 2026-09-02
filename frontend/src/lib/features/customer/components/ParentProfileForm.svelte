<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import EmailInput from '$lib/components/forms/fields/EmailInput.svelte';
	import PasswordInput from '$lib/components/forms/fields/PasswordInput.svelte';
    import TextInput from '$lib/components/forms/fields/TextInput.svelte';
    import CheckboxInput from '$lib/components/forms/fields/CheckboxInput.svelte';

	import type { FormErrors } from '$lib/types/forms';
	import { createFormState } from '$lib/utils/forms';

	let {
		handleSubmit,
		isLoading
	}: {
		handleSubmit: (body: Record<string, string>) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	// const initialBody: RegistrationRequest = {
	// 	email: '',
	// 	password: '',
    //     first_name: '',
    //     last_name: '',
    //     terms_accepted: false,
	// };


	// let body = $state<RegistrationRequest>(
	// 	createFormState(initialBody)
	// );

	// let errors = $state<FormErrors<RegistrationRequest>>({});

	// function validate(): boolean {
	// 	errors = {};

	// 	if (!body.email.trim()) {
	// 		errors.email = 'Email is required';
	// 	}

	// 	return Object.keys(errors).length === 0;
	// }

	// async function submit() {
	// 	if (!validate()) {
	// 		return;
	// 	}

	// 	await handleSubmit(body);
	// }

	// export function reset() {
	// 	body = createFormState(initialBody);
	// 	errors = {};
	// }
</script>

<!-- <Form 
    {isLoading}
    handleSubmit={submit}
>
    <p></p>
</Form> -->