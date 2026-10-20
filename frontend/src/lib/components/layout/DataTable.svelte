<!--
    A list of rows that each open a detail page. From md it's a table (the
    whole row is a link target, the first column holds the link itself); on
    a phone each row becomes a card with label | value lines. Staff lists
    use it so they work on a tablet or phone as well as a desktop.

    Values arrive formatted; the first column is the row's title.
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
	<p class="text-sm text-(--text-muted)">
		{empty}
	</p>
{:else}
	<!-- Phone: one card per row. -->
	<div class="flex flex-col gap-4 md:hidden">
		{#each rows as row (rowKey(row))}
			<Card border href={rowHref(row)}>
				<div class="flex flex-col gap-3">
					<p class="text-base font-semibold text-(--text)">
						{display(titleColumn.value(row))}
					</p>

					{#each detailColumns as column}
						<div class="flex flex-col gap-1">
							<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">
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
			<table class="w-full border-collapse text-left">
				<thead>
					<tr class="border-b border-(--border)">
						{#each columns as column}
							<th
								scope="col"
								class="px-5 py-3 text-xs font-extrabold uppercase tracking-wide text-(--text-muted)"
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
								'cursor-pointer transition hover:bg-(--primary-soft)',
								index < rows.length - 1 && 'border-b border-(--border)'
							]}
							onclick={(event) => {
								// The link in the first cell navigates by itself.
								if (!(event.target as Element).closest('a')) {
									void goto(rowHref(row));
								}
							}}
						>
							<td class="px-5 py-3">
								<a
									href={rowHref(row)}
									class="flex min-h-11 items-center text-base font-semibold text-(--text)"
								>
									{display(titleColumn.value(row))}
								</a>
							</td>

							{#each detailColumns as column}
								<td class="px-5 py-3 text-base text-(--text)">
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
