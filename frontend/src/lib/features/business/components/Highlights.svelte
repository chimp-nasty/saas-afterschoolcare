<!--
    The business's highlights under the public site's hero: each an icon, a
    title and a line, two to a row on a phone, all in one row from lg. The
    icon sits on the accent colour, softened (decoration only).
-->
<script lang="ts">
	import type { HighlightItem } from '$lib/api/schema';
	import { HIGHLIGHT_PRESETS } from '../highlights';

	let {
		highlights
	}: {
		highlights: HighlightItem[];
	} = $props();
</script>

<ul class="grid grid-cols-2 gap-x-4 gap-y-6 lg:grid-cols-4">
	{#each highlights as highlight, index (index)}
		{@const Icon = HIGHLIGHT_PRESETS[highlight.icon].icon}

		<li class="flex flex-col items-start gap-3">
			<span class="flex size-12 items-center justify-center rounded-2xl bg-(--accent-soft) text-(--primary)">
				<Icon size={24} aria-hidden="true" />
			</span>

			<div class="flex flex-col gap-1">
				<p class="text-base font-extrabold text-(--text)">{highlight.title}</p>
				<p class="text-sm text-(--text-muted)">{highlight.text}</p>
			</div>
		</li>
	{/each}
</ul>
