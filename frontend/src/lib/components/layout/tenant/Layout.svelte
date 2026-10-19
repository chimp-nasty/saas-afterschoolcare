<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		primaryColor,
		secondaryColor,
		header,
		sidebar,
		bottomNav,
		footer,
		children
	}: {
		primaryColor?: string | null;
		secondaryColor?: string | null;
		header?: Snippet;
		sidebar?: Snippet;
		// Mobile-only navigation (customers); see BottomNav.
		bottomNav?: Snippet;
		footer?: Snippet;
		children: Snippet;
	} = $props();
</script>

<div
	data-tenant-theme
	data-bottom-nav={bottomNav ? '' : undefined}
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
		<div class="flex flex-1 flex-col md:grid md:grid-cols-[16rem_1fr]">
			<aside class="hidden h-full md:block">
				{@render sidebar()}
			</aside>

			<main class="flex w-full min-w-0 flex-1 flex-col p-4">
				{@render children()}
			</main>
		</div>
	{:else}
		<main class="flex w-full min-w-0 flex-1 flex-col p-4">
			{@render children()}
		</main>
	{/if}

	{#if footer}
		<footer>
			{@render footer()}
		</footer>
	{/if}

	{@render bottomNav?.()}
</div>