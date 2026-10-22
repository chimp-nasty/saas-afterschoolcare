<!--
    The start of every staff kiosk task: "Who are you?", then your staff
    PIN. Only people on shift are offered (only they can act; clocking in is
    on the Shifts tab), which keeps the list short. Nothing is remembered
    after the task.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import PinEntry from './PinEntry.svelte';

	import type { StaffKioskMemberResponse } from '$lib/api/schema';

	let {
		members,
		task,
		adminsOnly = false,
		onverify,
		oncancel
	}: {
		members: StaffKioskMemberResponse[];
		// What they're about to do, e.g. "Emma Smith" or "your shift".
		task: string;
		// Only admins on shift (e.g. refunds).
		adminsOnly?: boolean;
		// Resolves to an error message, or null once the PIN is right.
		onverify: (member: StaffKioskMemberResponse, pin: string) => Promise<string | null>;
		oncancel: () => void;
	} = $props();

	const onShift = $derived(
		members.filter((member) => member.on_shift && member.has_pin && (!adminsOnly || member.is_admin))
	);

	let chosen = $state<StaffKioskMemberResponse | null>(null);
	let error = $state<string | null>(null);
	let busy = $state(false);

	async function submit(pin: string) {
		if (!chosen) return;

		busy = true;

		try {
			error = await onverify(chosen, pin);
		} finally {
			busy = false;
		}
	}
</script>

{#if !chosen}
	<div class="flex flex-col gap-6">
		<!-- A subtitle under the task window's title, never bigger than it. -->
		<div class="flex flex-col gap-1 text-center">
			<p class="text-lg font-semibold text-(--text)">Who are you?</p>
			<p class="text-lg text-(--text-muted)">For {task}</p>
		</div>

		<div class="grid grid-cols-2 gap-3">
			{#each onShift as member (member.user_id)}
				<button
					type="button"
					class="flex min-h-18 items-center justify-center rounded-lg border border-(--border) bg-(--surface) p-3 text-center transition active:bg-(--primary-soft)"
					onclick={() => {
						chosen = member;
						error = null;
					}}
				>
					<span class="text-lg font-extrabold text-(--text)">{member.first_name} {member.last_name}</span>
				</button>
			{:else}
				<div class="col-span-2">
					<EmptyState size="kiosk" message={adminsOnly ? 'No admin is clocked in.' : 'Nobody is clocked in.'} />
				</div>
			{/each}
		</div>

		<p class="text-center text-lg text-(--text-muted)">Not listed? Clock in on the Shifts tab.</p>

		<Button variant="ghost" fullWidth onclick={oncancel}>Cancel</Button>
	</div>
{:else}
	<PinEntry title={`${chosen.first_name}, enter your staff PIN`} {error} {busy} oncomplete={submit}>
		{#snippet footer()}
			<Button variant="ghost" fullWidth onclick={() => (chosen = null)}>Not me</Button>
		{/snippet}
	</PinEntry>
{/if}
