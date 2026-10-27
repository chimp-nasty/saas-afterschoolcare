<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		primaryColor,
		secondaryColor,
		accentColor,
		flush = false,
		header,
		sidebar,
		bottomNav,
		footer,
		children
	}: {
		primaryColor?: string | null;
		secondaryColor?: string | null;
		accentColor?: string | null;
		// The public site's pages (docs/public-site.md) lay out their own
		// full-width bands (SiteSection), so their main area has no padding.
		flush?: boolean;
		header?: Snippet;
		sidebar?: Snippet;
		// Mobile-only navigation (customers); see BottomNav.
		bottomNav?: Snippet;
		footer?: Snippet;
		children: Snippet;
	} = $props();

	const mainClass = $derived(['flex w-full min-w-0 flex-1 flex-col', flush ? '' : 'p-4']);
</script>

<div
	data-tenant-theme
	data-bottom-nav={bottomNav ? '' : undefined}
	class="relative flex min-h-screen flex-col"
	style:--primary={primaryColor ?? undefined}
	style:--secondary={secondaryColor ?? undefined}
	style:--accent={accentColor ?? undefined}
>
	<!-- Fixed to the top while the page scrolls. The wrapper sticks, not the
	     header inside it: a sticky element only sticks within its parent. -->
	{#if header}
		<div class="sticky top-0 z-40">
			{@render header()}
		</div>
	{/if}

	{#if sidebar}
		<div class="flex flex-1 flex-col md:grid md:grid-cols-[16rem_1fr]">
			<aside class="hidden h-full md:block">
				{@render sidebar()}
			</aside>

			<main class={mainClass}>
				{@render children()}
			</main>
		</div>
	{:else}
		<main class={mainClass}>
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
