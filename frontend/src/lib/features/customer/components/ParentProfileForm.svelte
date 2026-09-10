<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
    import SelectInput, { type SelectOption } from '$lib/components/forms/fields/SelectInput.svelte';
	import TextInput from '$lib/components/forms/fields/TextInput.svelte';

	import {
		updateCustomerProfileRequestSchema,
		type UpdateCustomerProfileRequest,
		type CustomerProfileResponse
	} from '$lib/api/public/types/customer';
	import type { CustomerProfileForm } from '../types';
	import { australianStateSchema } from '$lib/api/public/types/customer';

	import type { FormErrors } from '$lib/types/forms';
	import { validateForm } from '$lib/utils/forms';

	let {
		profile,
		handleSubmit,
		isLoading
	}: {
		profile: CustomerProfileResponse,
		handleSubmit: (body: UpdateCustomerProfileRequest) => void | Promise<void>;
		isLoading: boolean;
	} = $props();

	const stateOptions: SelectOption[] = australianStateSchema.options.map(
		(state) => ({
			value: state,
			label: state
		})
	);

	let body = $state<CustomerProfileForm>({
		phone: '',
		address_line_1: '',
		address_line_2: '',
		suburb: '',
		state: '',
		postcode: ''
	});

	$effect(() => {
		body.phone = profile.phone ?? '';
		body.address_line_1 = profile.address_line_1 ?? '';
		body.address_line_2 = profile.address_line_2 ?? '';
		body.suburb = profile.suburb ?? '';
		body.state = profile.state ?? '';
		body.postcode = profile.postcode ?? '';
	});

	let errors = $state<FormErrors<CustomerProfileForm>>({});

	async function submit() {
		const request: UpdateCustomerProfileRequest = {
			phone: body.phone || null,
			address_line_1: body.address_line_1 || null,
			address_line_2: body.address_line_2 || null,
			suburb: body.suburb || null,
			state: body.state || null,
			postcode: body.postcode || null
		};

		const validation = validateForm(
			updateCustomerProfileRequestSchema,
			request
		);

		errors = validation.errors;

		if (!validation.valid) return;
		await handleSubmit(request);
	}
</script>

<Form
	{isLoading}
	handleSubmit={submit}
>
	<TextInput 
		bind:value={body.phone}
		label="Phone Number"
		error={errors.phone}
	/>

	<TextInput 
		bind:value={body.address_line_1}
		label="Address Line 1"
		error={errors.address_line_1}
	/>

	<TextInput 
		bind:value={body.address_line_2}
		label="Address Line 2"
		error={errors.address_line_2}
		isRequired={false}
	/>

	<TextInput 
		bind:value={body.suburb}
		label="Suburb"
		error={errors.suburb}
	/>

	<SelectInput
		bind:value={body.state}
		label="State"
		error={errors.state}
		options={stateOptions}
	/>	

	<TextInput 
		bind:value={body.postcode}
		label="Postcode"
		error={errors.postcode}
	/>
</Form>