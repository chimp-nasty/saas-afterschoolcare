<!--
    Edit a child's profile: names and medical details. The date of birth is
    shown but can't be changed (staff correct it). Changing any medical
    detail sends the child back to staff for review (done by the server).
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { ChildResponse, UpdateChildRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type ChildProfileForm = {
		first_name: string;
		last_name: string;
		medical_info: string;
		allergy_info: string;
		medication_info: string;
	};

	let {
		child,
		onsubmit
	}: {
		child: ChildResponse;
		onsubmit: SubmitHandler<UpdateChildRequest>;
	} = $props();

	// Initial values only; after a save the inputs already hold what was saved.
	function toForm(): ChildProfileForm {
		return {
			first_name: child.first_name,
			last_name: child.last_name,
			medical_info: child.medical_info ?? '',
			allergy_info: child.allergy_info ?? '',
			medication_info: child.medication_info ?? ''
		};
	}

	let body = $state<ChildProfileForm>(toForm());
	let errors = $state<FormErrors<ChildProfileForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		const request: UpdateChildRequest = {
			first_name: body.first_name,
			last_name: body.last_name,
			medical_info: body.medical_info || null,
			allergy_info: body.allergy_info || null,
			medication_info: body.medication_info || null
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
	submitLabel="Save"
>
	<Field label="First name" error={errors.first_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" maxlength="100" bind:value={body.first_name} required />
		{/snippet}
	</Field>

	<Field label="Last name" error={errors.last_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" maxlength="100" bind:value={body.last_name} required />
		{/snippet}
	</Field>

	<Field label="Date of birth">
		{#snippet children(id)}
			<input {id} type="date" value={child.dob} disabled />
		{/snippet}
	</Field>

	<p class="text-sm text-(--text-muted)">
		Contact the centre to correct a date of birth. Changing the details
		below sends {child.first_name}'s profile to staff for review, and they
		can't be booked again until it's approved.
	</p>

	<Field label="Medical conditions" error={errors.medical_info}>
		{#snippet children(id)}
			<textarea {id} rows="4" bind:value={body.medical_info}></textarea>
		{/snippet}
	</Field>

	<Field label="Allergies" error={errors.allergy_info}>
		{#snippet children(id)}
			<textarea {id} rows="4" bind:value={body.allergy_info}></textarea>
		{/snippet}
	</Field>

	<Field label="Medication" error={errors.medication_info}>
		{#snippet children(id)}
			<textarea {id} rows="4" bind:value={body.medication_info}></textarea>
		{/snippet}
	</Field>
</Form>
