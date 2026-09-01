<script lang="ts">
	import type { Snippet } from 'svelte';
	import { afterNavigate } from '$app/navigation';
	import { fade, fly } from 'svelte/transition';

	let {
		open,
		onclose,
		children
	}: {
		open: boolean;
		onclose: () => void;
		children: Snippet;
	} = $props();

	afterNavigate(() => {
		if (open) {
			onclose();
		}
	});
</script>

{#if open}
	<div class="fixed inset-0 z-50 md:hidden">
		<button
			class="absolute inset-0 bg-black/20 backdrop-blur-sm"
			aria-label="Close navigation"
			onclick={onclose}
			transition:fade={{ duration: 200 }}
		></button>

		<div
			class="
				relative
				h-full
				w-4/5
				bg-(--surface)
				shadow-xl
			"
			transition:fly={{
				x: -320,
				duration: 250
			}}
		>
			{@render children()}
		</div>
	</div>
{/if}