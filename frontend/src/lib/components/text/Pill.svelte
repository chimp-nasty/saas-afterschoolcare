<!--
    A small status badge ("Here", "Medical", "New", "ID sighted"): one look
    everywhere, coloured by tone. The kiosk's is a size up, read at arm's
    length.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import { TONE_BOX, type TextSize, type Tone } from './textSize';

	let {
		tone = 'neutral',
		size = 'web',
		children
	}: {
		tone?: Tone;
		size?: TextSize;
		children: Snippet;
	} = $props();
</script>

<span
	class={[
		'inline-block w-fit shrink-0 rounded-full font-extrabold uppercase tracking-wide whitespace-nowrap',
		size === 'kiosk' ? 'px-3 py-1 text-sm' : 'px-2 py-0.5 text-xs',
		TONE_BOX[tone]
	]}
>
	{@render children()}
</span>
