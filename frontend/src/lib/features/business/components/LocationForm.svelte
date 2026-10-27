<!--
    A centre's details (Business settings › Centres): adding one, or editing
    it. Its web address is the code after the site's address (/varsity).
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';

	import {
		australianStateValues,
		businessLocationRequestTimezoneValues,
		type BusinessLocationRequest
	} from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		initial,
		submitLabel,
		onsubmit
	}: {
		initial?: BusinessLocationRequest;
		submitLabel: string;
		onsubmit: SubmitHandler<BusinessLocationRequest>;
	} = $props();

	const empty: BusinessLocationRequest = {
		name: '',
		code: '',
		address_line_1: '',
		address_line_2: null,
		suburb: '',
		state: 'QLD',
		postcode: '',
		phone: null,
		email: null,
		timezone: 'Australia/Brisbane'
	};

	// The saved details when the form opens; it then owns its edits.
	let body = $state<BusinessLocationRequest>(untrack(() => ({ ...(initial ?? empty) })));
	let errors = $state<FormErrors<BusinessLocationRequest>>({});
	let isLoading = $state(false);

	const timezoneLabel = (zone: string) => zone.replace('Australia/', '').replace('_', ' ');

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;

			// Adding: start again empty. Editing: keep what was saved.
			if (response.ok && !initial) {
				body = { ...empty };
			}
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} {submitLabel}>
	<Field label="Name" error={errors.name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" maxlength="200" bind:value={body.name} required />
		{/snippet}
	</Field>

	<Field label="Web address (after your site's address, e.g. varsity)" error={errors.code}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" autocapitalize="none" maxlength="50" pattern="[a-z][a-z0-9\-]*" bind:value={body.code} required />
		{/snippet}
	</Field>

	<Field label="Address" error={errors.address_line_1}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="address-line1" maxlength="255" bind:value={body.address_line_1} required />
		{/snippet}
	</Field>

	<Field label="Address line 2 (optional)" error={errors.address_line_2}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="address-line2" maxlength="255" bind:value={body.address_line_2} />
		{/snippet}
	</Field>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-3">
		<Field label="Suburb" error={errors.suburb}>
			{#snippet children(id)}
				<input {id} type="text" autocomplete="address-level2" maxlength="100" bind:value={body.suburb} required />
			{/snippet}
		</Field>

		<Field label="State" error={errors.state}>
			{#snippet children(id)}
				<Select {id} bind:value={body.state} options={australianStateValues.map((state) => ({ value: state, label: state }))} />
			{/snippet}
		</Field>

		<Field label="Postcode" error={errors.postcode}>
			{#snippet children(id)}
				<input {id} type="text" inputmode="numeric" autocomplete="postal-code" maxlength="4" bind:value={body.postcode} required />
			{/snippet}
		</Field>
	</div>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<Field label="Phone (optional)" error={errors.phone}>
			{#snippet children(id)}
				<input {id} type="tel" inputmode="tel" autocomplete="off" maxlength="50" bind:value={body.phone} />
			{/snippet}
		</Field>

		<Field label="Email (optional)" error={errors.email}>
			{#snippet children(id)}
				<input {id} type="email" inputmode="email" autocomplete="off" maxlength="255" bind:value={body.email} />
			{/snippet}
		</Field>
	</div>

	<Field label="Time zone" error={errors.timezone}>
		{#snippet children(id)}
			<Select {id} bind:value={body.timezone} options={businessLocationRequestTimezoneValues.map((zone) => ({ value: zone, label: timezoneLabel(zone) }))} />
		{/snippet}
	</Field>
</Form>
