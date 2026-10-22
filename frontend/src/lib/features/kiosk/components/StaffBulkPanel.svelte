<!--
    Several children at once at the staff kiosk, after the staff member's
    PIN: signing in a session's arrivals (after school care), or sending a
    before school session to school. Everyone eligible starts ticked; untick
    anyone absent. All or nothing: if one child can't be done, none are.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import CheckboxRow from '$lib/components/forms/CheckboxRow.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';

	import type { RunSheetEntryResponse } from '$lib/api/schema';

	let {
		action,
		date,
		candidates,
		busy,
		error,
		onsubmit,
		oncancel
	}: {
		action: 'sign_in' | 'to_school';
		date: string;
		candidates: RunSheetEntryResponse[];
		busy: boolean;
		error: string | null;
		onsubmit: (bookingIds: string[], at: string | null) => void;
		oncancel: () => void;
	} = $props();

	// Blank means now; otherwise when it happened on the run sheet's day.
	let time = $state('');
	// Everyone eligible when the task started; the list doesn't change under them.
	let ticked = $state<string[]>(untrack(() => candidates.map((entry) => entry.booking_id)));

	const verb = $derived(action === 'sign_in' ? 'Sign in' : 'Send');

	function toggle(bookingId: string) {
		ticked = ticked.includes(bookingId) ? ticked.filter((id) => id !== bookingId) : [...ticked, bookingId];
	}

	function submit() {
		onsubmit(ticked, time ? new Date(`${date}T${time}`).toISOString() : null);
	}
</script>

<div class="flex flex-col gap-5">
	<Field label="When (leave blank for now)">
		{#snippet children(id)}
			<input {id} type="time" bind:value={time} />
		{/snippet}
	</Field>

	<div class="flex flex-col gap-2">
		<p class="label-text">
			{action === 'sign_in' ? 'Arrived' : 'Going to school'} ({ticked.length} of {candidates.length})
		</p>

		<ul class="flex max-h-[45vh] flex-col overflow-y-auto rounded-lg border border-(--border)">
			{#each candidates as entry (entry.booking_id)}
				<li class="border-b border-(--border) px-4 py-1 last:border-b-0">
					<CheckboxRow
						checked={ticked.includes(entry.booking_id)}
						title={`${entry.child_first_name} ${entry.child_last_name}`}
						onchange={() => toggle(entry.booking_id)}
					/>
				</li>
			{/each}
		</ul>

		<div class="grid grid-cols-2 gap-3">
			<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (ticked = candidates.map((e) => e.booking_id))}>
				Select all
			</Button>
			<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (ticked = [])}>Select none</Button>
		</div>
	</div>

	<ErrorText size="kiosk" message={error} />

	<div class="grid grid-cols-2 gap-3">
		<Button variant="ghost" fullWidth isDisabled={busy} onclick={oncancel}>Cancel</Button>
		<Button fullWidth isLoading={busy} isDisabled={busy || !ticked.length} onclick={submit}>
			{verb} {ticked.length} {ticked.length === 1 ? 'child' : 'children'}{action === 'to_school' ? ' to school' : ''}
		</Button>
	</div>
</div>
