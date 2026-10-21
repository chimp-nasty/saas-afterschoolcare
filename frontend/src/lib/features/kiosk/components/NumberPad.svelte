<!--
    A large on-screen number pad (the tablet's own keyboard would cover the
    screen). Keys are at least 72px; the bottom-left key is the caller's
    (e.g. Clear), the bottom-right is backspace.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import { Delete } from 'lucide-svelte';

	let {
		disabled = false,
		ondigit,
		onbackspace,
		extra
	}: {
		disabled?: boolean;
		ondigit: (digit: string) => void;
		onbackspace: () => void;
		// The bottom-left key.
		extra?: Snippet;
	} = $props();

	const key =
		'flex min-h-18 items-center justify-center rounded-lg border border-(--border) bg-(--surface) text-3xl font-extrabold text-(--text) transition active:scale-[0.97] active:bg-(--primary-soft) disabled:opacity-50';
</script>

<div class="mx-auto grid w-full max-w-sm grid-cols-3 gap-3">
	{#each ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as digit (digit)}
		<button type="button" class={key} {disabled} onclick={() => ondigit(digit)}>
			{digit}
		</button>
	{/each}

	<div class="flex">
		{@render extra?.()}
	</div>

	<button type="button" class={key} {disabled} onclick={() => ondigit('0')}>0</button>

	<button type="button" class={key} {disabled} aria-label="Delete" onclick={onbackspace}>
		<Delete size={28} />
	</button>
</div>
