<!--
    The staff kiosk's run sheet before anyone enters a PIN: a tab per service
    running that day (before school, after school, vacation care), each a
    table with columns always aligned: place number, child (with markers
    for medical details and staff notes, no details), when they were signed in and by whom,
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
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Pill from '$lib/components/text/Pill.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { RunSheetEntryResponse, RunSheetSessionResponse } from '$lib/api/schema';
	import type { TextSize, Tone } from '$lib/components/text/textSize';
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
		onprint,
		size = 'kiosk'
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
		// The kiosk tablet's text, or the website's (the admin run sheet).
		size?: TextSize;
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

	// The run sheet's columns (GridTable keeps every row aligned and the same height).
	const columns = '2.5rem minmax(11rem,2fr) 5.5rem minmax(7rem,1fr) 5.5rem minmax(8rem,1.3fr) 6.5rem';

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

	const tone: Record<RollStatus, Tone> = {
		late: 'danger',
		here: 'success',
		gone: 'neutral',
		expected: 'warning'
	};

	// The counts under a session's title (late children follow, in red).
	function counts(group: RunSheetEntryResponse[]): string {
		const late = count(group, 'late');

		return `${group.length} booked · Not here ${count(group, 'expected')} · Here ${count(group, 'here') + late} · Gone ${count(group, 'gone')}`;
	}
</script>

{#snippet cells(entry: RunSheetEntryResponse, index: number)}
	{@const status = rollStatus(entry)}
	<span class="text-sm text-(--text-muted)" role="cell">{index + 1}</span>

	<span class="flex min-w-0 items-center gap-2" role="cell">
		<span class="truncate text-base font-semibold text-(--text)">
			{entry.child_first_name} {entry.child_last_name}
		</span>

		{#if entry.has_medical}
			<Pill tone="danger" {size}>Medical</Pill>
		{/if}

		{#if entry.has_notes}
			<Pill tone="neutral" {size}>Notes</Pill>
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
		<Pill tone={tone[status]} {size}>{ROLL_STATUS_LABELS[status]}</Pill>
	</span>
{/snippet}

{#if !sessions.length}
	<EmptyState {size} message="No sessions on this day." />
{:else}
	<TabbedPanels {tabs} {initialTab} bind:activeTab>
		{#snippet panel(id)}
			{@const session = sessions.find((s) => s.location_service_day_id === id)}
			{@const group = children[id] ?? []}
			{@const bulk = session ? bulkFor(session, group) : null}
			{@const note = session ? signingNote(session) : null}

			{#if session}
				<section class="flex flex-col gap-3">
					<SectionHeading
						title={`${session.service_name} · ${formatTimeRange(session.start_time, session.end_time)}`}
						{size}
					>
						{#snippet details()}
							{@const late = count(group, 'late')}
							{counts(group)}{#if late}
								· <span class="font-extrabold text-(--danger-text)">Late {late}</span>{/if}
						{/snippet}

						{#snippet actions()}
							{#if !session.is_open}
								<Pill tone="neutral" {size}>Closed</Pill>
							{/if}

							<p class={['text-(--text-muted)', size === 'kiosk' ? 'text-lg' : 'text-sm']}>{places(session)}</p>

							<Button variant="ghost" onclick={() => onprint(session)}>Print run sheet</Button>

							{#if onbulk && bulk && bulk.candidates.length}
								{#if note}
									<p class={['text-(--text-muted)', size === 'kiosk' ? 'text-lg' : 'text-sm']}>{note}</p>
								{:else}
									<Button onclick={() => onbulk(bulk.action, session, bulk.candidates)}>{bulk.label}</Button>
								{/if}
							{/if}
						{/snippet}
					</SectionHeading>

					<!-- 9 rows tall (one screen), then it scrolls; free places as blank rows. -->
					<GridTable
						items={group}
						key={(entry) => entry.booking_id}
						{columns}
						{headers}
						label={`${session.service_name} run sheet`}
						maxRows={9}
						minWidth="49rem"
						fillers={Math.max(session.capacity - group.length, 0)}
						onrowclick={onselect}
					>
						{#snippet row(entry, index)}
							{@render cells(entry, index)}
						{/snippet}
						{#snippet filler(place)}
							<span class="text-sm text-(--text-muted)" role="cell">{place}</span>
							<span class="text-base tracking-[0.5em] text-(--border)" role="cell">········</span>
						{/snippet}
					</GridTable>
				</section>
			{/if}
		{/snippet}
	</TabbedPanels>
{/if}
