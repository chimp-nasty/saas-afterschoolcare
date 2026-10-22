<!--
    The family's emergency contact: one person the centre calls when it
    can't reach the parent. Their name, phone (a valid Australian number,
    not the parent's own) and how they're related ("Other" asks for their
    own words). Needed before booking. Not a pickup person: being an
    emergency contact doesn't let anyone collect the children.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import {
		emergencyRelationValues,
		type CustomerProfileResponse,
		type EmergencyRelation,
		type UpdateCustomerProfileRequest
	} from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';
	import { EMERGENCY_RELATION_LABELS } from '../emergency';

	type EmergencyContactForm = {
		emergency_contact_name: string;
		emergency_contact_phone: string;
		emergency_contact_relation: EmergencyRelation | '';
		emergency_contact_relation_other: string;
	};

	let {
		profile,
		onsubmit
	}: {
		profile: CustomerProfileResponse;
		onsubmit: SubmitHandler<UpdateCustomerProfileRequest>;
	} = $props();

	// Initial values only; after a save the inputs already hold what was saved.
	function toForm(): EmergencyContactForm {
		return {
			emergency_contact_name: profile.emergency_contact_name ?? '',
			emergency_contact_phone: profile.emergency_contact_phone ?? '',
			emergency_contact_relation: profile.emergency_contact_relation ?? '',
			emergency_contact_relation_other: profile.emergency_contact_relation_other ?? ''
		};
	}

	let body = $state<EmergencyContactForm>(toForm());
	let errors = $state<FormErrors<EmergencyContactForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const isOther = body.emergency_contact_relation === 'other';
			const response = await onsubmit({
				emergency_contact_name: body.emergency_contact_name || null,
				emergency_contact_phone: body.emergency_contact_phone || null,
				emergency_contact_relation: body.emergency_contact_relation || null,
				emergency_contact_relation_other: isOther ? body.emergency_contact_relation_other || null : null
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save">
	<Field label="Name" error={errors.emergency_contact_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" maxlength="200" bind:value={body.emergency_contact_name} required />
		{/snippet}
	</Field>

	<Field label="Phone number" error={errors.emergency_contact_phone}>
		{#snippet children(id)}
			<input {id} type="tel" inputmode="tel" autocomplete="off" bind:value={body.emergency_contact_phone} required />
		{/snippet}
	</Field>

	<Field label="Relationship" error={errors.emergency_contact_relation}>
		{#snippet children(id)}
			<select {id} bind:value={body.emergency_contact_relation} required>
				<option value="">Select an option</option>
				{#each emergencyRelationValues as relation (relation)}
					<option value={relation}>{EMERGENCY_RELATION_LABELS[relation]}</option>
				{/each}
			</select>
		{/snippet}
	</Field>

	{#if body.emergency_contact_relation === 'other'}
		<Field label="How are they related?" error={errors.emergency_contact_relation_other}>
			{#snippet children(id)}
				<input {id} type="text" maxlength="100" bind:value={body.emergency_contact_relation_other} required />
			{/snippet}
		</Field>
	{/if}
</Form>
