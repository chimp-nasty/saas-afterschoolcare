<!--
    One child at the staff kiosk, once a staff member has entered their PIN
    for this task: where they're up to, and the staff actions for it
    (docs/kiosk-procedures.md, section 5). Signing out shows the family's
    pickup list with each person's photo ID status. Someone whose ID hasn't
    been sighted can still collect (approved without ID the first time), but
    every such sign-out asks first, until their ID is checked. Anyone else
    is a one-off release, which asks for the PIN again. Before school
    children can instead be sent to school. Brothers and sisters who are
    here are listed, ticked, and go with the same person in one request.

    Buttons are all one height, and either span the panel or take half of
    it, so they line up from card to card.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';
	import PickupIdPill from './PickupIdPill.svelte';

	import type { RollEntryResponse, RollPickupPersonResponse } from '$lib/api/schema';
	import { formatEnum, formatPhone, formatTimestamp } from '$lib/utils/helpers';
	import { formatClock } from '../kiosk';
	import { pickupIdStatus } from '../roll';

	type Release = { released_to_name: string; release_note: string };

	let {
		entry,
		date,
		pickups,
		siblings = [],
		busy,
		error,
		onsignin,
		oncollect,
		onrelease,
		oncheckid,
		onundo,
		canSendToSchool = false,
		onsendtoschool
	}: {
		entry: RollEntryResponse;
		date: string;
		// The family's pickup list.
		pickups: RollPickupPersonResponse[];
		// This family's other children who are here (signed in, not out).
		siblings?: RollEntryResponse[];
		busy: boolean;
		error: string | null;
		onsignin: (at: string | null) => void;
		// Signs out to this person, approving them without ID first if
		// they're not approved yet (already confirmed here).
		// `alsoBookingIds`: brothers and sisters going with them.
		oncollect: (person: RollPickupPersonResponse, at: string | null, alsoBookingIds: string[]) => void;
		onrelease: (release: Release, at: string | null, alsoBookingIds: string[]) => void;
		oncheckid: (person: RollPickupPersonResponse) => void;
		onundo: (step: 'sign_in' | 'sign_out') => void;
		// Before school care: they leave for school, not with a person.
		canSendToSchool?: boolean;
		onsendtoschool?: (at: string | null) => void;
	} = $props();

	// Blank means now; otherwise when it happened on the roll's day.
	let time = $state('');
	let signingOut = $state(false);
	let releasing = $state(false);
	let releasedTo = $state('');
	let releaseNote = $state('');
	// Everyone here starts ticked: siblings usually leave together.
	let also = $state<string[]>(untrack(() => siblings.map((sibling) => sibling.booking_id)));

	// "Emma", "Emma and Noah", "Emma, Noah and Ava".
	const going = $derived.by(() => {
		const names = [
			entry.child_first_name,
			...siblings.filter((s) => also.includes(s.booking_id)).map((s) => s.child_first_name)
		];

		return names.length === 1 ? names[0] : `${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}`;
	});

	function toggleSibling(bookingId: string) {
		also = also.includes(bookingId) ? also.filter((id) => id !== bookingId) : [...also, bookingId];
	}

	function at(): string | null {
		return time ? new Date(`${date}T${time}`).toISOString() : null;
	}

	async function collect(person: RollPickupPersonResponse) {
		if (pickupIdStatus(person) !== 'sighted') {
			const confirmed = await confirmAction({
				title: `Release ${going} to ${person.first_name} without ID?`,
				message: `${person.first_name}'s photo ID has never been sighted. Check it now if you can, using Photo ID checked. Only continue if ${person.first_name} is well known to the centre.`,
				confirmLabel: 'Collected without ID'
			});

			if (!confirmed) return;
		}

		oncollect(person, at(), also);
	}

	async function release() {
		const confirmed = await confirmAction({
			title: `Release ${going} to ${releasedTo}?`,
			message: `Only after you've phoned the account holder on the number in their account and checked ${releasedTo}'s photo ID. You'll enter your PIN again to confirm.`,
			confirmLabel: 'Release'
		});

		if (confirmed) {
			onrelease({ released_to_name: releasedTo, release_note: releaseNote }, at(), also);
		}
	}

	async function undo(step: 'sign_in' | 'sign_out') {
		const confirmed = await confirmAction({
			title: step === 'sign_out' ? 'Undo the sign-out?' : 'Undo the sign-in?',
			message: `${entry.child_first_name} will show as ${step === 'sign_out' ? 'still here' : 'not here yet'}. Do this only to correct a mistake.`,
			confirmLabel: 'Undo',
			tone: 'danger'
		});

		if (confirmed) onundo(step);
	}
</script>

<div class="flex flex-col gap-5">
	<div class="flex flex-col gap-1">
		<p class="text-base text-(--text-muted)">
			Family: {entry.family_first_name} {entry.family_last_name}
			{#if entry.family_phone}· {formatPhone(entry.family_phone)}{/if}
		</p>

		{#if entry.signed_in_at}
			<p class="text-lg text-(--text)">Signed in {formatClock(entry.signed_in_at)} by {entry.signed_in_by}</p>
		{/if}

		{#if entry.signed_out_at}
			<p class="text-lg text-(--text)">
				Signed out {formatClock(entry.signed_out_at)}
				{#if entry.collected_by}
					· collected by {entry.collected_by}
					{#if entry.collector_id_sighted === false}
						<span class="font-extrabold text-(--warning-text)">(⚠ ID not sighted)</span>
					{/if}
				{/if}
				{#if entry.released_to_name}· released to {entry.released_to_name} ({entry.release_note}){/if}
				{#if entry.sent_to_school}· sent to school{/if}
			</p>
		{/if}
	</div>

	{#if !entry.signed_out_at}
		<Field label="When (leave blank for now)">
			{#snippet children(id)}
				<input {id} type="time" bind:value={time} />
			{/snippet}
		</Field>
	{/if}

	{#if error}
		<p class="text-lg font-semibold text-(--danger-text)" role="alert">{error}</p>
	{/if}

	{#if !entry.signed_in_at}
		<Button fullWidth isLoading={busy} isDisabled={busy} onclick={() => onsignin(at())}>
			Sign in {entry.child_first_name}
		</Button>

	{:else if !entry.signed_out_at}
		{#if canSendToSchool && onsendtoschool}
			<Button fullWidth isDisabled={busy} onclick={() => onsendtoschool(at())}>
				Sent to school
			</Button>
		{/if}

		{#if !signingOut}
			<Button variant={canSendToSchool ? 'ghost' : 'default'} fullWidth isDisabled={busy} onclick={() => (signingOut = true)}>
				{canSendToSchool ? 'Collected by someone instead' : `Sign out ${entry.child_first_name}`}
			</Button>
		{:else}
			<div class="flex flex-col gap-3">
				{#if siblings.length}
					<div class="flex flex-col gap-2">
						<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Going with {entry.child_first_name}</p>
						<ul class="flex flex-col rounded-lg border border-(--border)">
							{#each siblings as sibling (sibling.booking_id)}
								<li class="border-b border-(--border) last:border-b-0">
									<label class="flex min-h-12 items-center gap-3 px-4 py-2">
										<input
											type="checkbox"
											class="size-5"
											checked={also.includes(sibling.booking_id)}
											onchange={() => toggleSibling(sibling.booking_id)}
										/>
										<span class="text-base font-semibold text-(--text)">{sibling.child_first_name} {sibling.child_last_name}</span>
										<span class="text-sm text-(--text-muted)">{sibling.service_name}</span>
									</label>
								</li>
							{/each}
						</ul>
					</div>
				{/if}

				<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Collected by</p>

				{#each pickups as person (person.pickup_person_id)}
					{@const status = pickupIdStatus(person)}
					<div class="flex flex-col gap-3 rounded-lg border border-(--border) p-3">
						<div class="flex flex-col gap-1">
							<p class="text-lg font-semibold text-(--text)">{person.first_name} {person.last_name}</p>
							<p class="text-sm text-(--text-muted)">{formatEnum(person.relation)} · {formatPhone(person.phone)}</p>
							<PickupIdPill {person} />
							{#if status === 'not_sighted' && person.staff_approved_at}
								<p class="text-sm text-(--text-muted)">Approved without ID {formatTimestamp(person.staff_approved_at)}</p>
							{/if}
						</div>

						<!-- Collected always takes the right-hand half. -->
						<div class="grid grid-cols-2 gap-3">
							{#if status === 'sighted'}
								<span></span>
							{:else}
								<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => oncheckid(person)}>
									Photo ID checked
								</Button>
							{/if}

							<Button fullWidth isDisabled={busy} onclick={() => collect(person)}>
								{status === 'not_approved' ? 'Collected without ID' : 'Collected'}
							</Button>
						</div>
					</div>
				{/each}

				{#if !releasing}
					<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (releasing = true)}>
						Someone else (one-off release)
					</Button>
				{:else}
					<div class="flex flex-col gap-3 rounded-lg border border-(--border) p-3">
						<p class="text-sm text-(--text-muted)">
							Phone the account holder on the number in their account first, then check this person's photo ID.
						</p>
						<Field label="Their full name">
							{#snippet children(id)}
								<input {id} type="text" maxlength="200" autocomplete="off" bind:value={releasedTo} />
							{/snippet}
						</Field>
						<Field label="How it was confirmed">
							{#snippet children(id)}
								<textarea {id} rows="2" maxlength="1000" placeholder="e.g. Phoned Jo Smith 5:40pm; licence checked" bind:value={releaseNote}></textarea>
							{/snippet}
						</Field>
						<div class="grid grid-cols-2 gap-3">
							<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => (releasing = false)}>Cancel</Button>
							<Button fullWidth isDisabled={busy || !releasedTo.trim() || !releaseNote.trim()} onclick={release}>
								Release {also.length ? `${also.length + 1} children` : entry.child_first_name}
							</Button>
						</div>
					</div>
				{/if}
			</div>
		{/if}

		<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => undo('sign_in')}>Undo sign-in</Button>

	{:else}
		<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => undo('sign_out')}>Undo sign-out</Button>
	{/if}
</div>
