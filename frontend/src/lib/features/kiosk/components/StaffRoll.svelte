<!--
    The staff kiosk's run sheet before anyone enters a PIN: a tab per service
    running that day (before school, after school, vacation care), each a
    table with columns always aligned: place number, child (with a marker
    for medical details, no details), when they were signed in and by whom,
    when they left and who took them (names shortened, "Sam L."), and where
    they're up to. Booked children come first, alphabetically, then empty
    rows up to the session's capacity (each service has its own). Tapping a
    child starts a task for them. After school care offers signing in its
    arrivals together, and before school care sending its children to
    school together.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import TabbedPanels from '$lib/components/controls/TabbedPanels.svelte';

	import type { RunSheetEntryResponse, RunSheetSessionResponse } from '$lib/api/schema';
	import { formatTimeRange } from '$lib/utils/helpers';
	import { formatClock } from '../kiosk';
	import { rollStatus, ROLL_STATUS_LABELS, type RollStatus } from '../roll';

	let {
		sessions,
		entries,
		isToday,
		isPast,
		onselect,
		onbulk,
		onprint
	}: {
		sessions: RunSheetSessionResponse[];
		entries: RunSheetEntryResponse[];
		// The day shown, relative to the location's today.
		isToday: boolean;
		isPast: boolean;
		// Tapping a child (the kiosk); without it the rows are read-only.
		onselect?: (entry: RunSheetEntryResponse) => void;
		// Several children at once: who's eligible, all ticked to start.
		// Without it, no bulk actions (the admin run sheet is read-only).
		onbulk?: (action: BulkAction, session: RunSheetSessionResponse, candidates: RunSheetEntryResponse[]) => void;
		// The printable run sheet for this session (asks for a PIN).
		onprint: (session: RunSheetSessionResponse) => void;
	} = $props();

	type BulkAction = 'sign_in' | 'to_school';

	// Outside the session's signing times (when the centre has them on),
	// what to say instead of the bulk button.
	function signingNote(session: RunSheetSessionResponse): string | null {
		const now = Date.now();

		if (session.signing_opens_at && now < Date.parse(session.signing_opens_at)) {
			return `Signing opens at ${formatClock(session.signing_opens_at)}`;
		}

		if (session.signing_closes_at && now > Date.parse(session.signing_closes_at)) {
			return `Signing closed at ${formatClock(session.signing_closes_at)}`;
		}

		return null;
	}

	// Which services offer which bulk action, and who's eligible for it.
	function bulkFor(session: RunSheetSessionResponse, group: RunSheetEntryResponse[]) {
		if (session.service_code === 'after_school_care') {
			const candidates = group.filter((entry) => rollStatus(entry) === 'expected');

			return { action: 'sign_in' as BulkAction, label: `Sign in arrivals (${candidates.length})`, candidates };
		}

		if (session.service_code === 'before_school_care') {
			const candidates = group.filter((entry) => ['here', 'late'].includes(rollStatus(entry)));

			return { action: 'to_school' as BulkAction, label: `Send to school (${candidates.length})`, candidates };
		}

		return null;
	}

	// One template for the header and every row, so columns line up.
	const columns =
		'grid grid-cols-[2.5rem_minmax(11rem,2fr)_5.5rem_minmax(7rem,1fr)_5.5rem_minmax(8rem,1.3fr)_6.5rem] items-center gap-x-4';

	const headers = ['#', 'Child', 'In', 'Signed in by', 'Out', 'Collected by', 'Status'];

	function inSession(entry: RunSheetEntryResponse, session: RunSheetSessionResponse): boolean {
		return (
			entry.service_name === session.service_name &&
			entry.start_time === session.start_time &&
			entry.end_time === session.end_time
		);
	}

	// Each session's children, alphabetically.
	const children = $derived(
		Object.fromEntries(
			sessions.map((session) => [
				session.location_service_day_id,
				entries
					.filter((entry) => inSession(entry, session))
					.sort((a, b) =>
						`${a.child_first_name} ${a.child_last_name}`.localeCompare(`${b.child_first_name} ${b.child_last_name}`)
					)
			])
		) as Record<string, RunSheetEntryResponse[]>
	);

	function count(group: RunSheetEntryResponse[], status: RollStatus) {
		return group.filter((entry) => rollStatus(entry) === status).length;
	}

	const tabs = $derived(
		sessions.map((session) => {
			const late = count(children[session.location_service_day_id] ?? [], 'late');

			return {
				id: session.location_service_day_id,
				label: `${session.service_name} (${session.booked}/${session.capacity})${late ? ` · Late ${late}` : ''}`
			};
		})
	);

	// "HH:MM:SS" now, at the tablet (it's at the centre, like session times).
	function clockNow(): string {
		return new Date().toTimeString().slice(0, 8);
	}

	// Today: the session running now, else the next one, else the last.
	// Another day: the first.
	const initialTab = $derived.by(() => {
		if (!sessions.length) return undefined;
		if (!isToday) return sessions[0].location_service_day_id;

		const now = clockNow();
		const current = sessions.find((s) => s.start_time <= now && now < s.end_time);
		const next = sessions.find((s) => now < s.start_time);

		return (current ?? next ?? sessions[sessions.length - 1]).location_service_day_id;
	});

	let activeTab = $state<string | undefined>(undefined);

	// The free places' numbers, after the booked children, up to capacity.
	function emptyPlaces(session: RunSheetSessionResponse, group: RunSheetEntryResponse[]): number[] {
		return Array.from({ length: Math.max(session.capacity - group.length, 0) }, (_, index) => group.length + index + 1);
	}

	function places(session: RunSheetSessionResponse): string {
		if (isPast) return `${session.capacity} places`;

		const left = `${session.places_left} ${session.places_left === 1 ? 'spot' : 'spots'} remaining`;

		return session.awaiting_payment ? `${left} · ${session.awaiting_payment} awaiting payment` : left;
	}

	function collectedBy(entry: RunSheetEntryResponse): string {
		if (entry.collected_by) return `${entry.collected_by}${entry.collector_id_sighted === false ? ' ⚠' : ''}`;
		if (entry.released_to) return `${entry.released_to} (one-off)`;
		if (entry.sent_to_school) return 'To school';

		return '—';
	}

	const pill: Record<RollStatus, string> = {
		late: 'bg-(--danger-soft) text-(--danger-text)',
		here: 'bg-(--success-soft) text-(--success-text)',
		gone: 'bg-(--surface-muted) text-(--text-muted)',
		expected: 'bg-(--warning-soft) text-(--warning-text)'
	};
</script>

{#snippet cells(entry: RunSheetEntryResponse, index: number)}
	{@const status = rollStatus(entry)}
	<span class="text-sm text-(--text-muted)" role="cell">{index + 1}</span>

	<span class="flex min-w-0 items-center gap-2" role="cell">
		<span class="truncate text-base font-semibold text-(--text)">
			{entry.child_first_name} {entry.child_last_name}
		</span>

		{#if entry.has_medical}
			<span class="shrink-0 rounded-full bg-(--danger-soft) px-2 py-0.5 text-xs font-extrabold uppercase tracking-wide text-(--danger-text)">
				Medical
			</span>
		{/if}
	</span>

	<span class="text-base text-(--text)" role="cell">
		{entry.signed_in_at ? formatClock(entry.signed_in_at) : '—'}
	</span>
	<span class="truncate text-base text-(--text-muted)" role="cell">{entry.signed_in_by ?? '—'}</span>

	<span class="text-base text-(--text)" role="cell">
		{entry.signed_out_at ? formatClock(entry.signed_out_at) : '—'}
	</span>
	<span
		class={[
			'truncate text-base',
			entry.collector_id_sighted === false ? 'font-semibold text-(--warning-text)' : 'text-(--text-muted)'
		]}
		role="cell"
	>
		{entry.signed_out_at ? collectedBy(entry) : '—'}
	</span>

	<span role="cell">
		<span class={['inline-block rounded-full px-3 py-1 text-sm font-extrabold', pill[status]]}>
			{ROLL_STATUS_LABELS[status]}
		</span>
	</span>
{/snippet}

{#if !sessions.length}
	<p class="text-center text-xl text-(--text-muted)">No sessions on this day.</p>
{:else}
	<TabbedPanels {tabs} {initialTab} bind:activeTab>
		{#snippet panel(id)}
			{@const session = sessions.find((s) => s.location_service_day_id === id)}
			{@const group = children[id] ?? []}
			{@const bulk = session ? bulkFor(session, group) : null}
			{@const note = session ? signingNote(session) : null}

			{#if session}
				<section class="flex flex-col gap-3">
					<div class="flex flex-wrap items-baseline justify-between gap-2">
						<div class="flex flex-col gap-1">
							<h2 class="text-xl font-extrabold text-(--text)">
								{session.service_name} · {formatTimeRange(session.start_time, session.end_time)}
								{#if !session.is_open}
									<span class="ml-2 rounded-full bg-(--surface-muted) px-3 py-1 text-sm font-extrabold uppercase text-(--text-muted)">Closed</span>
								{/if}
							</h2>
							<p class="text-base text-(--text-muted)">
								{group.length} booked · Not here {count(group, 'expected')} · Here {count(group, 'here') + count(group, 'late')} · Gone {count(group, 'gone')}
								{#if count(group, 'late')}
									· <span class="font-extrabold text-(--danger-text)">Late {count(group, 'late')}</span>
								{/if}
							</p>
						</div>

						<div class="flex flex-wrap items-center gap-3">
							<p class="text-base text-(--text-muted)">{places(session)}</p>

							<Button variant="ghost" onclick={() => onprint(session)}>Print run sheet</Button>

							{#if onbulk && bulk && bulk.candidates.length}
								{#if note}
									<p class="text-base text-(--text-muted)">{note}</p>
								{:else}
									<Button onclick={() => onbulk(bulk.action, session, bulk.candidates)}>{bulk.label}</Button>
								{/if}
							{/if}
						</div>
					</div>

					<!-- A fixed height of 9 rows that scrolls (one screen), with the headers
					     pinned; sideways too on a phone. -->
					<div class="max-h-[29.5rem] overflow-auto rounded-2xl border border-(--border) bg-(--surface)">
						<div class="min-w-[49rem]" role="table" aria-label={`${session.service_name} run sheet`}>
							<div class={[columns, 'sticky top-0 z-10 border-b border-(--border) bg-(--surface-muted) px-5 py-2']} role="row">
								{#each headers as header (header)}
									<span class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)" role="columnheader">{header}</span>
								{/each}
							</div>

							{#each group as entry, index (entry.booking_id)}
								{#if onselect}
									<button
										type="button"
										class={[columns, 'min-h-12 w-full border-b border-(--border) px-5 py-2 text-left last:border-b-0 active:bg-(--primary-soft)']}
										role="row"
										onclick={() => onselect(entry)}
									>
										{@render cells(entry, index)}
									</button>
								{:else}
									<div class={[columns, 'min-h-12 border-b border-(--border) px-5 py-2 last:border-b-0']} role="row">
										{@render cells(entry, index)}
									</div>
								{/if}
							{/each}

							<!-- The places still free, up to this session's capacity. -->
							{#each emptyPlaces(session, group) as place (place)}
								<div class={[columns, 'min-h-12 border-b border-(--border) px-5 py-2 last:border-b-0']} role="row">
									<span class="text-sm text-(--text-muted)" role="cell">{place}</span>
									<span class="text-base tracking-[0.5em] text-(--border)" role="cell">········</span>
								</div>
							{/each}
						</div>
					</div>
				</section>
			{/if}
		{/snippet}
	</TabbedPanels>
{/if}
