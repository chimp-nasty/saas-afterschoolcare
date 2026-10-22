<!--
    The app's table for lists whose rows are read across (run sheets, staff,
    service days, action plans). One column template for the header and
    every row, so columns always line up, and every row the same fixed
    height: each cell is one line, vertically centred, and anything too long
    is cut off with "…", so a tick, a dash or a button never changes a row's
    height. A 48px button or checkbox fits a row.

    Rows are tappable when `onrowclick` is given, otherwise read-only.
    `maxRows` gives the table a fixed height that scrolls, with the headers
    pinned. `fillers` adds blank numbered rows after the items (e.g. a
    session's free places). On a phone the table scrolls sideways inside
    itself (`minWidth`).

    Usage:
        <GridTable items={staff} key={(s) => s.user_id} {columns} {headers} empty="No staff yet.">
            {#snippet row(s)}
                <span>{s.first_name}</span> …
            {/snippet}
        </GridTable>
-->
<script lang="ts" module>
	// Every row (and the header) is exactly this tall: room for a 48px button.
	export const ROW_HEIGHT_REM = 3.5;
	const HEADER_HEIGHT_REM = 2.5;
</script>

<script lang="ts" generics="T">
	import type { Snippet } from 'svelte';

	import EmptyState from '$lib/components/text/EmptyState.svelte';

	let {
		items,
		key,
		columns,
		headers,
		label,
		row,
		filler,
		fillers = 0,
		empty,
		maxRows,
		minWidth = '40rem',
		onrowclick,
		rowClass
	}: {
		items: T[];
		key: (item: T) => string;
		// A CSS grid-template-columns value, e.g. "2.5rem minmax(11rem,2fr) 5.5rem".
		columns: string;
		headers: string[];
		// What the table is, for screen readers.
		label: string;
		// One row's cells, one element per column.
		row: Snippet<[T, number]>;
		// A blank row's cells, given its number (after the items).
		filler?: Snippet<[number]>;
		fillers?: number;
		// Shown when there are no items and no fillers.
		empty?: string;
		// Fixed height with a scroll after this many rows.
		maxRows?: number;
		minWidth?: string;
		onrowclick?: (item: T) => void;
		// Extra classes for an item's row (e.g. faded past days).
		rowClass?: (item: T) => string | false | null | undefined;
	} = $props();

	const gridStyle = $derived(`grid-template-columns: ${columns};`);
	const heightStyle = $derived(
		maxRows ? `max-height: ${HEADER_HEIGHT_REM + maxRows * ROW_HEIGHT_REM + 0.1}rem;` : ''
	);
	const fillerNumbers = $derived(Array.from({ length: Math.max(fillers, 0) }, (_, i) => items.length + i + 1));

	// Each cell: one line, centred, cut off with "…" (grid items are blocks).
	const rowBase =
		'grid h-14 w-full items-center gap-x-4 border-b border-(--border) px-5 text-left last:border-b-0 *:min-w-0 *:truncate';
</script>

<div class="overflow-auto rounded-2xl border border-(--border) bg-(--surface)" style={heightStyle}>
	<div style={`min-width: ${minWidth};`} role="table" aria-label={label}>
		<div
			class="sticky top-0 z-10 grid h-10 items-center gap-x-4 border-b border-(--border) bg-(--surface-muted) px-5 *:min-w-0 *:truncate"
			style={gridStyle}
			role="row"
		>
			{#each headers as header, index (index)}
				<span class="label-text" role="columnheader">{header}</span>
			{/each}
		</div>

		{#each items as item, index (key(item))}
			{#if onrowclick}
				<button
					type="button"
					class={[rowBase, 'active:bg-(--primary-soft)', rowClass?.(item)]}
					style={gridStyle}
					role="row"
					onclick={() => onrowclick(item)}
				>
					{@render row(item, index)}
				</button>
			{:else}
				<div class={[rowBase, rowClass?.(item)]} style={gridStyle} role="row">
					{@render row(item, index)}
				</div>
			{/if}
		{/each}

		{#if filler}
			{#each fillerNumbers as number (number)}
				<div class={rowBase} style={gridStyle} role="row">
					{@render filler(number)}
				</div>
			{/each}
		{/if}

		{#if !items.length && !fillers && empty}
			<div class="px-5 py-4"><EmptyState message={empty} /></div>
		{/if}
	</div>
</div>
