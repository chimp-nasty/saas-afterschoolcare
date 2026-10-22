<!--
    A list of rows that each open a detail page. From md it's a table (the
    whole row is a link target, the first column holds the link itself); on
    a phone each row becomes a card with label | value lines. Staff lists
    use it so they work on a tablet or phone as well as a desktop.

    Values arrive formatted; the first column is the row's title. As in
    GridTable, every table row is the same fixed height: one line per cell,
    cut off with "…" if it's too long.
-->
<script lang="ts" module>
	export type DataTableColumn<T> = {
		label: string;
		value: (row: T) => string | number | null | undefined;
	};
</script>

<script lang="ts" generics="T">
	import { goto } from '$app/navigation';

	import Card from './Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';

	let {
		rows,
		columns,
		rowKey,
		rowHref,
		empty
	}: {
		rows: T[];
		columns: DataTableColumn<T>[];
		rowKey: (row: T) => string;
		rowHref: (row: T) => string;
		// Shown when there are no rows.
		empty: string;
	} = $props();

	const [titleColumn, ...detailColumns] = $derived(columns);

	function display(value: string | number | null | undefined): string | number {
		return value === null || value === undefined || value === '' ? '—' : value;
	}
</script>

{#if rows.length === 0}
	<EmptyState message={empty} />
{:else}
	<!-- Phone: one card per row. -->
	<div class="flex flex-col gap-4 md:hidden">
		{#each rows as row (rowKey(row))}
			<Card border href={rowHref(row)}>
				<div class="flex flex-col gap-3">
					<p class="text-base font-semibold text-(--text)">
						{display(titleColumn.value(row))}
					</p>

					{#each detailColumns as column (column.label)}
						<div class="flex flex-col gap-1">
							<p class="label-text">
								{column.label}
							</p>

							<p class="text-base text-(--text)">
								{display(column.value(row))}
							</p>
						</div>
					{/each}
				</div>
			</Card>
		{/each}
	</div>

	<!-- Tablet and desktop: a table; tapping anywhere on a row opens it. -->
	<div class="hidden md:block">
		<Card border padded={false}>
			<table class="w-full table-fixed border-collapse text-left">
				<thead>
					<tr class="border-b border-(--border)">
						{#each columns as column (column.label)}
							<th
								scope="col"
								class="h-10 truncate px-5 label-text"
							>
								{column.label}
							</th>
						{/each}
					</tr>
				</thead>

				<tbody>
					{#each rows as row, index (rowKey(row))}
						<tr
							class={[
								'h-14 cursor-pointer transition hover:bg-(--primary-soft)',
								index < rows.length - 1 && 'border-b border-(--border)'
							]}
							onclick={(event) => {
								// The link in the first cell navigates by itself.
								if (!(event.target as Element).closest('a')) {
									void goto(rowHref(row));
								}
							}}
						>
							<td class="truncate px-5">
								<a
									href={rowHref(row)}
									class="block truncate leading-[3.5rem] text-base font-semibold text-(--text)"
								>
									{display(titleColumn.value(row))}
								</a>
							</td>

							{#each detailColumns as column (column.label)}
								<td class="truncate px-5 text-base text-(--text)">
									{display(column.value(row))}
								</td>
							{/each}
						</tr>
					{/each}
				</tbody>
			</table>
		</Card>
	</div>
{/if}
