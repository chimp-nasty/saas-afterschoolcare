<!--
    The kiosk's full screen: the centre's name across the top, an optional
    right-hand area (e.g. "Logged in as Jo · Done"), and the current step.
    Large text throughout: it's read standing up, at arm's length.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		centreName,
		label,
		actions,
		children
	}: {
		centreName: string;
		// e.g. "Staff kiosk"
		label?: string;
		actions?: Snippet;
		children: Snippet;
	} = $props();
</script>

<div class="flex min-h-[calc(100dvh-2rem)] flex-col gap-6">
	<header class="flex flex-wrap items-center justify-between gap-4 border-b border-(--border) pb-4">
		<div class="flex flex-col">
			<p class="text-2xl font-extrabold text-(--primary)">{centreName}</p>

			{#if label}
				<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">{label}</p>
			{/if}
		</div>

		{#if actions}
			<div class="flex flex-wrap items-center gap-3">
				{@render actions()}
			</div>
		{/if}
	</header>

	<div class="flex flex-1 flex-col">
		{@render children()}
	</div>
</div>
