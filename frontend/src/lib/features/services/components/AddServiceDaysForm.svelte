<!--
    Add a service's days (superadmins): every chosen weekday between two
    dates with the same places, or one date (`single`). Days that already
    exist are skipped, and the page says which.
-->
<script lang="ts">
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { CreateServiceDaysRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type AddDaysForm = {
		date_from: string;
		date_to: string;
		weekdays: number[];
		capacity: string;
	};

	let {
		single = false,
		onsubmit
	}: {
		// One date (e.g. a vacation care day) instead of a range of weekdays.
		single?: boolean;
		onsubmit: SubmitHandler<Omit<CreateServiceDaysRequest, 'location_service_id'>>;
	} = $props();

	const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];

	let body = $state<AddDaysForm>({ date_from: '', date_to: '', weekdays: [0, 1, 2, 3, 4], capacity: '' });
	let errors = $state<FormErrors<AddDaysForm>>({});
	let isLoading = $state(false);

	function toggle(day: number) {
		body.weekdays = body.weekdays.includes(day) ? body.weekdays.filter((d) => d !== day) : [...body.weekdays, day];
	}

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				date_from: body.date_from,
				date_to: single ? body.date_from : body.date_to,
				weekdays: single ? [0, 1, 2, 3, 4, 5, 6] : body.weekdays,
				capacity: Number(body.capacity)
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel={single ? 'Add day' : 'Add days'}>
	{#if single}
		<Field label="Date" error={errors.date_from}>
			{#snippet children(id)}
				<input {id} type="date" bind:value={body.date_from} required />
			{/snippet}
		</Field>
	{:else}
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

		<fieldset class="flex flex-col gap-2">
			<legend class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Weekdays</legend>
			<div class="flex flex-wrap gap-3">
				{#each WEEKDAYS as label, day (label)}
					<label class="flex min-h-12 items-center gap-2">
						<input type="checkbox" class="size-5" checked={body.weekdays.includes(day)} onchange={() => toggle(day)} />
						<span class="text-base text-(--text)">{label}</span>
					</label>
				{/each}
			</div>
			{#if errors.weekdays}<p class="text-sm text-(--danger-text)">{errors.weekdays}</p>{/if}
		</fieldset>
	{/if}

	<Field label="Places" error={errors.capacity}>
		{#snippet children(id)}
			<input {id} type="number" inputmode="numeric" min="0" step="1" bind:value={body.capacity} required />
		{/snippet}
	</Field>
</Form>
