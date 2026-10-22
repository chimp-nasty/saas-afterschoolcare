<!--
    Label and value pairs ("Name: Sam Lee"), one under another or, with
    `columns`, side by side. Labels are the label role; values are body text
    in semibold. A missing value shows "—". Pass `value` as text, or a
    snippet when it needs markup.
-->
<script lang="ts" module>
	import type { Snippet } from 'svelte';

	export type LabelValueItem = {
		label: string;
		value?: string | number | null;
		// Instead of `value`, for markup (a link, a pill, a list).
		content?: Snippet;
	};
</script>

<script lang="ts">
	let {
		items,
		columns = 1
	}: {
		items: LabelValueItem[];
		columns?: 1 | 2 | 3;
	} = $props();

	const grid: Record<number, string> = {
		1: 'grid-cols-1',
		2: 'grid-cols-1 md:grid-cols-2',
		3: 'grid-cols-1 md:grid-cols-3'
	};
</script>

<dl class={['grid gap-x-6 gap-y-3', grid[columns]]}>
	{#each items as item (item.label)}
		<div class="flex min-w-0 flex-col gap-1">
			<dt class="label-text">{item.label}</dt>
			<dd class="text-base font-semibold break-words text-(--text)">
				{#if item.content}
					{@render item.content()}
				{:else}
					{item.value === null || item.value === undefined || item.value === '' ? '—' : item.value}
				{/if}
			</dd>
		</div>
	{/each}
</dl>
