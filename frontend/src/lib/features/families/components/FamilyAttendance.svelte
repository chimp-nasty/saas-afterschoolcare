<!--
    A family's attendance history in Admin › Families, newest first: when
    each child was signed in and out and by whom, who collected them (with
    whether their ID had been sighted), one-off releases, to school, and
    late finishes. Changes are made at the staff kiosk, not here.
-->
<script lang="ts">
	import GridTable from '$lib/components/layout/GridTable.svelte';

	import type { FamilyAttendanceResponse } from '$lib/api/schema';
	import { formatClock } from '$lib/features/kiosk/kiosk';
	import { formatDate } from '$lib/utils/helpers';

	let {
		entries
	}: {
		entries: FamilyAttendanceResponse[];
	} = $props();

	function at(time: string | null, by: string | null): string {
		if (!time) return '—';

		return by ? `${formatClock(time)} · ${by}` : formatClock(time);
	}

	function collected(entry: FamilyAttendanceResponse): string {
		if (entry.sent_to_school) return 'To school';
		if (entry.released_to_name) return `${entry.released_to_name} (one-off: ${entry.release_note ?? ''})`;
		if (entry.collected_by) return `${entry.collected_by} ${entry.collector_id_sighted ? '✓' : '⚠ ID not sighted'}`;

		return '—';
	}

	const columns =
		'minmax(8rem,1fr) minmax(8rem,1fr) minmax(9rem,1.2fr) minmax(9rem,1.1fr) minmax(9rem,1.1fr) minmax(12rem,1.6fr) 5rem';
</script>

<GridTable
	items={entries}
	key={(entry) => entry.booking_id}
	{columns}
	headers={['Date', 'Child', 'Service', 'In', 'Out', 'Collected by', 'Late']}
	label="Attendance history"
	minWidth="62rem"
	maxRows={12}
	empty="No sessions in this range."
>
	{#snippet row(entry)}
		<span class="text-base font-semibold text-(--text)" role="cell">{formatDate(entry.service_date)}</span>
		<span class="text-base text-(--text)" role="cell">{entry.child_first_name}</span>
		<span class="text-base text-(--text)" role="cell">{entry.service_name}</span>
		<span class="text-base text-(--text)" role="cell">
			{entry.signed_in_at ? at(entry.signed_in_at, entry.signed_in_by) : 'Not here'}
		</span>
		<span class="text-base text-(--text)" role="cell">{at(entry.signed_out_at, entry.signed_out_by)}</span>
		<span
			class={['text-base', entry.collector_id_sighted === false ? 'font-semibold text-(--warning-text)' : 'text-(--text)']}
			role="cell"
		>
			{collected(entry)}
		</span>
		<span class={['text-base', entry.left_late ? 'font-extrabold text-(--danger-text)' : 'text-(--text-muted)']} role="cell">
			{entry.left_late ? 'Late' : '—'}
		</span>
	{/snippet}
</GridTable>
