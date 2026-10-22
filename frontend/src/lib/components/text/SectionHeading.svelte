<!--
    A section's title, with an optional one-line description and actions
    beside it (e.g. a button). The section title role: text-lg extrabold;
    the description is secondary text. Use it for every titled part of a
    page, panel or card that a page is built from. `details` replaces the
    plain `description` when part of it needs markup (e.g. a count in red).
    The kiosk's is a size up.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import type { TextSize } from './textSize';

	let {
		title,
		description,
		details,
		size = 'web',
		actions
	}: {
		title: string;
		description?: string | null;
		details?: Snippet;
		size?: TextSize;
		actions?: Snippet;
	} = $props();
</script>

<div class="flex flex-wrap items-end justify-between gap-x-4 gap-y-2">
	<div class="flex min-w-0 flex-col gap-1">
		<h2 class={['font-extrabold text-(--text)', size === 'kiosk' ? 'text-xl' : 'text-lg']}>{title}</h2>

		{#if details || description}
			<p class={['text-(--text-muted)', size === 'kiosk' ? 'text-lg' : 'text-sm']}>
				{#if details}
					{@render details()}
				{:else}
					{description}
				{/if}
			</p>
		{/if}
	</div>

	{#if actions}
		<div class="flex flex-wrap items-center gap-3">{@render actions()}</div>
	{/if}
</div>
