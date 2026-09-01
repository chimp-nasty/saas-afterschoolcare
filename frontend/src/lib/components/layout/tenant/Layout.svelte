<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		primaryColor,
		secondaryColor,
		header,
		sidebar,
		footer,
		children
	}: {
		primaryColor?: string | null;
		secondaryColor?: string | null;
		header?: Snippet;
		sidebar?: Snippet;
		footer?: Snippet;
		children: Snippet;
	} = $props();
</script>

<div
	class="relative flex min-h-screen flex-col"
	style:--primary={primaryColor ?? undefined}
	style:--secondary={secondaryColor ?? undefined}
>
	{#if header}
		<header class="relative">
			{@render header()}
		</header>
	{/if}

	{#if sidebar}
		<div class="flex-1 md:grid md:grid-cols-[16rem_1fr]">
			<aside class="hidden h-full md:block">
				{@render sidebar()}
			</aside>

			<main class="w-full min-w-0 p-4">
				{@render children()}
			</main>
		</div>
	{:else}
		<main class="w-full min-w-0 flex-1 p-4">
			{@render children()}
		</main>
	{/if}

	{#if footer}
		<footer>
			{@render footer()}
		</footer>
	{/if}
</div>