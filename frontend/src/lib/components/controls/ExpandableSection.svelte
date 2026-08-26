<script lang="ts">
	import type { Snippet } from 'svelte';

	import Button from '../actions/Button.svelte';

	let {
		title,
		defaultOpen = false,
		children,
		actions
	}: {
		title: string;
		defaultOpen?: boolean;
		children?: Snippet;
		actions?: Snippet;
	} = $props();

	let isOpen = $state(defaultOpen);
</script>

<div class="flex flex-col">
	<div class="flex items-center justify-between gap-2">
		<Button
			variant="hyperlink"
			onclick={() => (isOpen = !isOpen)}
		>
			{title}
		</Button>

		{#if actions}
			{@render actions()}
		{/if}
	</div>

	{#if isOpen}
		<div class="mt-2">
			{@render children?.()}
		</div>
	{/if}
</div>