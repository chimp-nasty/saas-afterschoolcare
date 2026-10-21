<!--
    The printable run sheet, for marking off by pen at the collection point
    (and the paper fallback in docs/kiosk-procedures.md). Hidden on screen,
    and moved to the end of <body> so that when the page prints, everything
    else is left out (routes/layout.css, .print-sheet).
    Each session prints as whole pages of ROWS_PER_PAGE one-line rows:
    children alphabetically, then blank numbered rows to the bottom of the
    last page (one page at least; another full page only when the children
    don't fit). Times already recorded are printed; the rest is for pen. It has families' phone numbers, so the kiosk prints it
    only after a staff PIN.
-->
<script lang="ts">
	import type { RollEntryResponse, RollFamilyResponse, RollPickupPersonResponse } from '$lib/api/schema';
	import { formatDate, formatPhone, formatTimeRange } from '$lib/utils/helpers';
	import { formatClock } from '$lib/features/kiosk/kiosk';
	import { portal } from '$lib/utils/portal';

	export type PrintSession = {
		name: string;
		startTime: string | null;
		endTime: string | null;
		entries: RollEntryResponse[];
	};

	// Rows that fit a landscape A4 page at the fixed row height below.
	const ROWS_PER_PAGE = 22;

	let {
		centreName,
		date,
		sessions,
		families
	}: {
		centreName: string;
		date: string;
		sessions: PrintSession[];
		families: RollFamilyResponse[];
	} = $props();

	function sorted(entries: RollEntryResponse[]): RollEntryResponse[] {
		return [...entries].sort((a, b) =>
			`${a.child_first_name} ${a.child_last_name}`.localeCompare(`${b.child_first_name} ${b.child_last_name}`)
		);
	}

	function approvedPickups(entry: RollEntryResponse): RollPickupPersonResponse[] {
		const pickups = families.find((family) => family.family_user_id === entry.family_user_id)?.pickups ?? [];

		return pickups.filter((person) => person.staff_approved_at);
	}

	function firstWord(name: string | null): string {
		return name?.split(' ')[0] ?? '';
	}

	function departed(entry: RollEntryResponse): string {
		if (!entry.signed_out_at) return '';

		const by = entry.sent_to_school
			? 'to school'
			: entry.released_to_name
				? `${entry.released_to_name} (one-off)`
				: `${firstWord(entry.collected_by)}${entry.collector_id_sighted === false ? ' ⚠' : ''}`;

		return `${formatClock(entry.signed_out_at)} ${by}`;
	}

	// The session's pages: its children in order, then blank rows (null)
	// filling the last page.
	function pages(session: PrintSession): (RollEntryResponse | null)[][] {
		const children = sorted(session.entries);
		const count = Math.max(1, Math.ceil(children.length / ROWS_PER_PAGE));
		const rows = [...children, ...Array(count * ROWS_PER_PAGE - children.length).fill(null)];

		return Array.from({ length: count }, (_, page) => rows.slice(page * ROWS_PER_PAGE, (page + 1) * ROWS_PER_PAGE));
	}
</script>

<div class="print-sheet hidden" use:portal>
	{#each sessions as session (session.name)}
		{@const sessionPages = pages(session)}
		{#each sessionPages as rows, pageIndex (pageIndex)}
			<section class="print-page">
				<header class="mb-3 flex items-baseline justify-between gap-4">
					<h1 class="text-lg font-extrabold">
						{centreName} · Run sheet · {formatDate(date)} · {session.name}{#if session.startTime && session.endTime}
							· {formatTimeRange(session.startTime, session.endTime)}{/if}
					</h1>
					<p class="text-xs">
						Page {pageIndex + 1} of {sessionPages.length}
					</p>
				</header>

				<table>
					<colgroup>
						<col style="width: 4%" />
						<col style="width: 17%" />
						<col style="width: 33%" />
						<col style="width: 12%" />
						<col style="width: 11%" />
						<col style="width: 15%" />
						<col style="width: 8%" />
					</colgroup>
					<thead>
						<tr>
							<th>#</th>
							<th>Child</th>
							<th>Approved pickups (✓ ID sighted, ⚠ not)</th>
							<th>Family phone</th>
							<th>In</th>
							<th>Out / by</th>
							<th>Staff</th>
						</tr>
					</thead>
					<tbody>
						{#each rows as entry, rowIndex (rowIndex)}
							<tr>
								<td>{pageIndex * ROWS_PER_PAGE + rowIndex + 1}</td>
								{#if entry}
									<td class="font-semibold">{entry.child_first_name} {entry.child_last_name}</td>
									<td>
										{approvedPickups(entry)
											.map((person) => `${person.first_name} ${person.last_name} ${person.identity_verified_at ? '✓' : '⚠'}`)
											.join(', ')}
									</td>
									<td>{entry.family_phone ? formatPhone(entry.family_phone) : ''}</td>
									<td>{entry.signed_in_at ? `${formatClock(entry.signed_in_at)} ${firstWord(entry.signed_in_by)}` : '☐'}</td>
									<td>{entry.signed_out_at ? departed(entry) : '☐'}</td>
									<td></td>
								{:else}
									<td></td>
									<td></td>
									<td></td>
									<td>☐</td>
									<td>☐</td>
									<td></td>
								{/if}
							</tr>
						{/each}
					</tbody>
				</table>
			</section>
		{/each}
	{/each}
</div>

<style>
	/* Printed paper, not the screen theme: black on white, ruled cells. */
	.print-sheet {
		color: #000;
		background: #fff;
	}

	/* Fixed columns and one-line rows of a fixed height, so exactly
	   ROWS_PER_PAGE rows fit a page; longer text is cut off with "…". */
	.print-sheet table {
		width: 100%;
		border-collapse: collapse;
		table-layout: fixed;
		font-size: 9pt;
	}

	.print-sheet th,
	.print-sheet td {
		border: 1px solid #000;
		padding: 0 4px;
		height: 7mm;
		text-align: left;
		vertical-align: middle;
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.print-page + .print-page {
		break-before: page;
	}
</style>
