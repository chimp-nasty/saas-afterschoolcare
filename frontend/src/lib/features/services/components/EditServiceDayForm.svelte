<!--
    One service day (superadmins): its places, open or closed, and why it's
    closed. The database refuses places below what's booked and closing a
    booked day. A day that's never been booked can also be deleted.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { ServiceDayOverviewResponse, UpdateServiceDayRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type EditDayForm = {
		capacity: string;
		is_open: boolean;
		closed_reason: string;
	};

	let {
		day,
		onsubmit,
		ondelete
	}: {
		day: ServiceDayOverviewResponse;
		onsubmit: SubmitHandler<UpdateServiceDayRequest>;
		// Only for a day that's never been booked.
		ondelete?: () => void;
	} = $props();

	// Initial values only.
	function toForm(): EditDayForm {
		return { capacity: String(day.capacity), is_open: day.is_open, closed_reason: day.closed_reason ?? '' };
	}

	let body = $state<EditDayForm>(toForm());
	let errors = $state<FormErrors<EditDayForm>>({});
	let isLoading = $state(false);

	const held = $derived(day.booked + day.awaiting_payment);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				capacity: Number(body.capacity),
				is_open: body.is_open,
				closed_reason: body.is_open ? null : body.closed_reason
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<div class="flex flex-col gap-4">
	<p class="text-sm text-(--text-muted)">
		{day.booked} booked{#if day.awaiting_payment} · {day.awaiting_payment} awaiting payment{/if} · places can't go below {held}.
	</p>

	<Form {isLoading} handleSubmit={submit} submitLabel="Save">
		<Field label="Places" error={errors.capacity}>
			{#snippet children(id)}
				<input {id} type="number" inputmode="numeric" min={held} step="1" bind:value={body.capacity} required />
			{/snippet}
		</Field>

		<label class="flex min-h-12 items-center gap-3">
			<input type="checkbox" class="size-5" bind:checked={body.is_open} />
			<span class="flex flex-col">
				<span class="text-base font-semibold text-(--text)">Open for bookings</span>
				{#if day.is_open && held > 0}
					<span class="text-sm text-(--text-muted)">Children are booked: refund them before closing this day.</span>
				{/if}
			</span>
		</label>

		{#if !body.is_open}
			<Field label="Why it's closed (optional)" error={errors.closed_reason}>
				{#snippet children(id)}
					<input {id} type="text" maxlength="200" placeholder="e.g. Staff training" bind:value={body.closed_reason} />
				{/snippet}
			</Field>
		{/if}
	</Form>

	{#if ondelete}
		<Button variant="ghost" fullWidth onclick={ondelete}>Delete this day</Button>
	{/if}
</div>
