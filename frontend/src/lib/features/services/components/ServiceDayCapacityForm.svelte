<!--
    The same places for every day of a service in a date range
    (superadmins). All or nothing: if any day has more places booked than
    the new number, nothing changes and those days are named.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { SetServiceDayCapacityRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type CapacityForm = {
		date_from: string;
		date_to: string;
		capacity: string;
	};

	let {
		onsubmit
	}: {
		onsubmit: SubmitHandler<Omit<SetServiceDayCapacityRequest, 'location_service_id'>>;
	} = $props();

	let body = $state<CapacityForm>({ date_from: '', date_to: '', capacity: '' });
	let errors = $state<FormErrors<CapacityForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				date_from: body.date_from,
				date_to: body.date_to,
				capacity: Number(body.capacity)
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Change places">
	<div class="grid grid-cols-2 gap-4">
		<Field label="From" error={errors.date_from}>
			{#snippet children(id)}
				<input {id} type="date" bind:value={body.date_from} required />
			{/snippet}
		</Field>
		<Field label="To" error={errors.date_to}>
			{#snippet children(id)}
				<input {id} type="date" min={body.date_from || undefined} bind:value={body.date_to} required />
			{/snippet}
		</Field>
	</div>

	<Field label="Places on every day" error={errors.capacity}>
		{#snippet children(id)}
			<input {id} type="number" inputmode="numeric" min="0" step="1" bind:value={body.capacity} required />
		{/snippet}
	</Field>
</Form>
