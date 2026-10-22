<!--
    Four PIN dots over a number pad. Submits itself on the fourth digit and
    clears, ready for another try if the caller shows an error.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import ErrorText from '$lib/components/text/ErrorText.svelte';
	import NumberPad from './NumberPad.svelte';

	let {
		title,
		error = null,
		busy = false,
		oncomplete,
		footer
	}: {
		title: string;
		error?: string | null;
		busy?: boolean;
		oncomplete: (pin: string) => void | Promise<void>;
		// Below the pad (e.g. Forgot PIN, Back).
		footer?: Snippet;
	} = $props();

	let pin = $state('');

	async function digit(value: string) {
		if (pin.length >= 4) return;

		pin += value;

		if (pin.length === 4) {
			const entered = pin;
			pin = '';
			await oncomplete(entered);
		}
	}
</script>

<div class="flex flex-col items-center gap-6">
	<h1 class="text-center text-3xl font-extrabold text-(--text)">{title}</h1>

	<div class="flex gap-5" aria-label={`${pin.length} of 4 digits entered`}>
		{#each [0, 1, 2, 3] as index (index)}
			<span
				class={[
					'size-5 rounded-full border-2 border-(--primary)',
					index < pin.length && 'bg-(--primary)'
				]}
			></span>
		{/each}
	</div>

	{#if error}
		<div class="max-w-md text-center">
			<ErrorText size="kiosk" message={error} />
		</div>
	{/if}

	<NumberPad disabled={busy} ondigit={digit} onbackspace={() => (pin = pin.slice(0, -1))} />

	{@render footer?.()}
</div>
