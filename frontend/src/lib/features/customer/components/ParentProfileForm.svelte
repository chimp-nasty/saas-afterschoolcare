<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import {
		australianStateValues,
		type AustralianState,
		type UpdateCustomerProfileRequest,
		type CustomerProfileResponse
	} from '$lib/api/schema';

	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type CustomerProfileForm = {
		phone: string;
		address_line_1: string;
		address_line_2: string;
		suburb: string;
		state: AustralianState | '';
		postcode: string;
	};

	let {
		profile,
		onsubmit
	}: {
		profile: CustomerProfileResponse;
		onsubmit: SubmitHandler<UpdateCustomerProfileRequest>;
	} = $props();

	// Initial values only; after a save the inputs already hold what was saved.
	function toForm(): CustomerProfileForm {
		return {
			phone: profile.phone ?? '',
			address_line_1: profile.address_line_1 ?? '',
			address_line_2: profile.address_line_2 ?? '',
			suburb: profile.suburb ?? '',
			state: profile.state ?? '',
			postcode: profile.postcode ?? ''
		};
	}

	let body = $state<CustomerProfileForm>(toForm());
	let errors = $state<FormErrors<CustomerProfileForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		const request: UpdateCustomerProfileRequest = {
			phone: body.phone || null,
			address_line_1: body.address_line_1 || null,
			address_line_2: body.address_line_2 || null,
			suburb: body.suburb || null,
			state: body.state || null,
			postcode: body.postcode || null
		};

		isLoading = true;

		try {
			const response = await onsubmit(request);

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form
	{isLoading}
	handleSubmit={submit}
>
	<Field label="Phone Number" error={errors.phone}>
		{#snippet children(id)}
			<input {id} type="tel" autocomplete="tel" bind:value={body.phone} required />
		{/snippet}
	</Field>

	<Field label="Address Line 1" error={errors.address_line_1}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="address-line1" bind:value={body.address_line_1} required />
		{/snippet}
	</Field>

	<Field label="Address Line 2" error={errors.address_line_2}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="address-line2" bind:value={body.address_line_2} />
		{/snippet}
	</Field>

	<Field label="Suburb" error={errors.suburb}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="address-level2" bind:value={body.suburb} required />
		{/snippet}
	</Field>

	<Field label="State" error={errors.state}>
		{#snippet children(id)}
			<select {id} bind:value={body.state} required>
				<option value="">Select an option</option>
				{#each australianStateValues as state (state)}
					<option value={state}>{state}</option>
				{/each}
			</select>
		{/snippet}
	</Field>

	<Field label="Postcode" error={errors.postcode}>
		{#snippet children(id)}
			<input {id} type="text" inputmode="numeric" autocomplete="postal-code" bind:value={body.postcode} required />
		{/snippet}
	</Field>
</Form>