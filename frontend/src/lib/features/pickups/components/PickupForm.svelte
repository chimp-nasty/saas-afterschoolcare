<!--
    Add or edit a pickup person. Adding asks for the account holder's two
    declarations (they agreed, they're 18 or over); editing doesn't. The page
    decides what to send and whether to confirm first.
-->
<script lang="ts" module>
	import type { PickupRelation } from '$lib/api/schema';

	// What the form hands the page: the add page adds the two declarations,
	// the edit page sends it as an update.
	export type PickupFormValues = {
		first_name: string;
		last_name: string;
		phone: string;
		email: string;
		relation: PickupRelation;
		relation_other: string | null;
	};
</script>

<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import { pickupRelationValues, type PickupResponse } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';
	import { PICKUP_RELATION_LABELS } from '../types';

	type PickupFormBody = {
		first_name: string;
		last_name: string;
		phone: string;
		email: string;
		relation: PickupRelation | '';
		relation_other: string;
		consent_confirmed: boolean;
		adult_confirmed: boolean;
	};

	let {
		pickup,
		onsubmit
	}: {
		// Set when editing.
		pickup?: PickupResponse;
		onsubmit: SubmitHandler<PickupFormValues>;
	} = $props();

	const isEditing = $derived(pickup !== undefined);

	// The account holder is added automatically, never chosen.
	const relationOptions = pickupRelationValues.filter(
		(relation) => relation !== 'account_holder'
	);

	// Initial values only; after a save the inputs already hold what was saved.
	function toForm(): PickupFormBody {
		return {
			first_name: pickup?.first_name ?? '',
			last_name: pickup?.last_name ?? '',
			phone: pickup?.phone ?? '',
			email: pickup?.email ?? '',
			relation: pickup?.relation ?? '',
			relation_other: pickup?.relation_other ?? '',
			consent_confirmed: false,
			adult_confirmed: false
		};
	}

	let body = $state<PickupFormBody>(toForm());
	let errors = $state<FormErrors<PickupFormBody>>({});
	let isLoading = $state(false);

	const name = $derived(body.first_name.trim() || 'They');

	async function submit() {
		errors = {};

		// The select is required, so a relation is always chosen here.
		const values: PickupFormValues = {
			first_name: body.first_name,
			last_name: body.last_name,
			phone: body.phone,
			email: body.email,
			relation: body.relation as PickupRelation,
			relation_other: body.relation === 'other' ? body.relation_other : null
		};

		isLoading = true;

		try {
			const response = await onsubmit(values);

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

	<Field label="Mobile number" error={errors.phone}>
		{#snippet children(id)}
			<input {id} type="tel" inputmode="tel" autocomplete="off" bind:value={body.phone} required />
		{/snippet}
	</Field>

	<Field label="Email" error={errors.email}>
		{#snippet children(id)}
			<input {id} type="email" inputmode="email" autocomplete="off" maxlength="255" bind:value={body.email} required />
		{/snippet}
	</Field>

	<p class="text-sm text-(--text-muted)">
		Their kiosk PIN is emailed here, never shown in the app.
	</p>

	<Field label="Relationship" error={errors.relation}>
		{#snippet children(id)}
			<Select
				{id}
				bind:value={body.relation}
				required
				placeholder="Select a relationship"
				options={relationOptions.map((relation) => ({ value: relation, label: PICKUP_RELATION_LABELS[relation] }))}
			/>
		{/snippet}
	</Field>

	{#if body.relation === 'other'}
		<Field label="Describe the relationship" error={errors.relation_other}>
			{#snippet children(id)}
				<input {id} type="text" maxlength="100" bind:value={body.relation_other} required />
			{/snippet}
		</Field>
	{/if}

	{#if !isEditing}
		<Field label={`${name} agreed to be a pickup person for my children`} error={errors.consent_confirmed} inline>
			{#snippet children(id)}
				<input {id} type="checkbox" bind:checked={body.consent_confirmed} required />
			{/snippet}
		</Field>

		<Field label={`${name} is 18 or over`} error={errors.adult_confirmed} inline>
			{#snippet children(id)}
				<input {id} type="checkbox" bind:checked={body.adult_confirmed} required />
			{/snippet}
		</Field>
	{/if}
</Form>
