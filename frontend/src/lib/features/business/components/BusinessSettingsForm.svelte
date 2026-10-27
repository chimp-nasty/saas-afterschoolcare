<!--
    The business's details (Business settings › Business details): its
    trading and legal names, ABN, contact details and a short introduction
    for families. The ABN is checked by the server.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { BusinessSettingsRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		initial,
		onsubmit
	}: {
		initial: BusinessSettingsRequest;
		onsubmit: SubmitHandler<BusinessSettingsRequest>;
	} = $props();

	// The saved details when the form opens; it then owns its edits.
	let body = $state<BusinessSettingsRequest>(untrack(() => ({ ...initial })));
	let errors = $state<FormErrors<BusinessSettingsRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ ...body });

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save details">
	<Field label="Business name (what families see)" error={errors.name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="organization" maxlength="200" bind:value={body.name} required />
		{/snippet}
	</Field>

	<Field label="Legal name" error={errors.legal_name}>
		{#snippet children(id)}
			<input {id} type="text" autocomplete="off" maxlength="200" bind:value={body.legal_name} />
		{/snippet}
	</Field>

	<Field label="ABN" error={errors.abn}>
		{#snippet children(id)}
			<input {id} type="text" inputmode="numeric" autocomplete="off" maxlength="14" bind:value={body.abn} />
		{/snippet}
	</Field>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-2">
		<Field label="Email" error={errors.email}>
			{#snippet children(id)}
				<input {id} type="email" inputmode="email" autocomplete="email" maxlength="255" bind:value={body.email} />
			{/snippet}
		</Field>

		<Field label="Phone" error={errors.phone}>
			{#snippet children(id)}
				<input {id} type="tel" inputmode="tel" autocomplete="tel" maxlength="50" bind:value={body.phone} />
			{/snippet}
		</Field>
	</div>
</Form>
