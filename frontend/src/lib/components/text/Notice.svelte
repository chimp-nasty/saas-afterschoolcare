<!--
    A coloured box with one message about how things stand ("Emma signed
    out", "Not yet reviewed by admin", "Medical details: see the Medical
    tab"). One tone each: success, warning, danger or neutral. Optional
    actions sit at its right (e.g. "See medical").
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import { TONE_BOX, type TextSize, type Tone } from './textSize';

	let {
		tone = 'neutral',
		size = 'web',
		children,
		actions
	}: {
		tone?: Tone;
		size?: TextSize;
		children: Snippet;
		actions?: Snippet;
	} = $props();
</script>

<div
	class={[
		'flex items-center justify-between gap-3 rounded-lg px-4 py-3 font-semibold',
		size === 'kiosk' ? 'text-lg' : 'text-sm',
		TONE_BOX[tone]
	]}
	role={tone === 'danger' ? 'alert' : 'status'}
>
	<p class="min-w-0">{@render children()}</p>

	{#if actions}
		<div class="shrink-0">{@render actions()}</div>
	{/if}
</div>
