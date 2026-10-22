<!--
    One service's settings in Admin › Service settings: whether it's
    offered, its price, session times, description and policies. Saving a
    new price or new times asks first, because they reach families
    differently: a price applies to new bookings only (bookings keep the
    price they were paid at), new times apply to every booking.
-->
<script lang="ts">
	import CheckboxRow from '$lib/components/forms/CheckboxRow.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';

	import type { LocationServiceSettingsResponse, UpdateLocationServiceConfigRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type ServiceSettingsForm = {
		is_active: boolean;
		price: string;
		start_time: string;
		end_time: string;
		description: string;
		refund_cutoff_days: string;
		min_child_age: string;
		max_child_age: string;
		late_fee: string;
		late_fee_grace_minutes: string;
	};

	let {
		service,
		onsubmit
	}: {
		service: LocationServiceSettingsResponse;
		onsubmit: SubmitHandler<UpdateLocationServiceConfigRequest>;
	} = $props();

	const dollars = (cents: number) => (cents / 100).toFixed(2);
	const cents = (value: string) => Math.round(Number(value) * 100);

	// Initial values only; after a save the inputs already hold what was saved.
	function toForm(): ServiceSettingsForm {
		return {
			is_active: service.is_active,
			price: dollars(service.current_price_cents),
			start_time: service.start_time.slice(0, 5),
			end_time: service.end_time.slice(0, 5),
			description: service.description ?? '',
			refund_cutoff_days: String(service.refund_cutoff_days),
			min_child_age: String(service.min_child_age),
			max_child_age: String(service.max_child_age),
			late_fee: dollars(service.late_fee_cents),
			late_fee_grace_minutes: String(service.late_fee_grace_minutes)
		};
	}

	let body = $state<ServiceSettingsForm>(toForm());
	let errors = $state<FormErrors<ServiceSettingsForm>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};

		const priceChanged = cents(body.price) !== service.current_price_cents;
		const timesChanged =
			body.start_time !== service.start_time.slice(0, 5) || body.end_time !== service.end_time.slice(0, 5);

		if (priceChanged || timesChanged) {
			const changes = [
				priceChanged && 'The new price applies to new bookings only; existing bookings keep what they paid.',
				timesChanged && 'The new times apply to every booking, including ones already made.'
			].filter(Boolean);

			const confirmed = await confirmAction({
				title: `Save ${service.service_name}?`,
				message: changes.join(' '),
				confirmLabel: 'Save'
			});

			if (!confirmed) return;
		}

		isLoading = true;

		try {
			const response = await onsubmit({
				is_active: body.is_active,
				current_price_cents: cents(body.price),
				start_time: body.start_time,
				end_time: body.end_time,
				description: body.description,
				refund_cutoff_days: Number(body.refund_cutoff_days),
				min_child_age: Number(body.min_child_age),
				max_child_age: Number(body.max_child_age),
				late_fee_cents: cents(body.late_fee),
				late_fee_grace_minutes: Number(body.late_fee_grace_minutes)
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save">
	<CheckboxRow
		bind:checked={body.is_active}
		title="Offered to families"
		help="Untick to stop new bookings. Existing bookings aren't changed."
	/>

	<Field label="Price per session ($)" error={errors.price}>
		{#snippet children(id)}
			<input {id} type="number" inputmode="decimal" min="0" step="0.01" bind:value={body.price} required />
		{/snippet}
	</Field>

	<div class="grid grid-cols-2 gap-4">
		<Field label="Starts" error={errors.start_time}>
			{#snippet children(id)}
				<input {id} type="time" bind:value={body.start_time} required />
			{/snippet}
		</Field>
		<Field label="Finishes" error={errors.end_time}>
			{#snippet children(id)}
				<input {id} type="time" bind:value={body.end_time} required />
			{/snippet}
		</Field>
	</div>

	<Field label="Description (shown to families)" error={errors.description}>
		{#snippet children(id)}
			<textarea {id} rows="3" maxlength="1000" bind:value={body.description}></textarea>
		{/snippet}
	</Field>

	<Field label="Families can refund until (days before the session)" error={errors.refund_cutoff_days}>
		{#snippet children(id)}
			<input {id} type="number" inputmode="numeric" min="0" step="1" bind:value={body.refund_cutoff_days} required />
		{/snippet}
	</Field>

	<div class="grid grid-cols-2 gap-4">
		<Field label="Youngest age" error={errors.min_child_age}>
			{#snippet children(id)}
				<input {id} type="number" inputmode="numeric" min="0" step="1" bind:value={body.min_child_age} required />
			{/snippet}
		</Field>
		<Field label="Oldest age" error={errors.max_child_age}>
			{#snippet children(id)}
				<input {id} type="number" inputmode="numeric" min="0" step="1" bind:value={body.max_child_age} required />
			{/snippet}
		</Field>
	</div>

	<div class="grid grid-cols-2 gap-4">
		<Field label="Late fee ($, 0 for none)" error={errors.late_fee}>
			{#snippet children(id)}
				<input {id} type="number" inputmode="decimal" min="0" step="0.01" bind:value={body.late_fee} required />
			{/snippet}
		</Field>
		<Field label="Late fee after (minutes)" error={errors.late_fee_grace_minutes}>
			{#snippet children(id)}
				<input {id} type="number" inputmode="numeric" min="0" step="1" bind:value={body.late_fee_grace_minutes} required />
			{/snippet}
		</Field>
	</div>

	<p class="text-sm text-(--text-muted)">Late fees are shown to families but not charged yet.</p>
</Form>
