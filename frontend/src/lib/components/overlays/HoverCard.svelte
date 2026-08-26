<script lang="ts">
	import type { Snippet } from 'svelte';

	import Card from '$lib/components/layout/Card.svelte';

	let {
		trigger,
		children
	}: {
		trigger: Snippet;
		children: Snippet;
	} = $props();

	let open = $state(false);
</script>

<!-- svelte-ignore a11y_no_static_element_interactions -->
<div
	class="relative inline-block"
	onmouseenter={() => (open = true)}
	onmouseleave={() => (open = false)}
>
	{@render trigger()}

	{#if open}
		<div
			class="
				absolute
				bottom-full
				left-1/2
				z-50
				-translate-x-1/2
				pb-2
			"
		>
			<Card>
				{@render children()}
			</Card>
		</div>
	{/if}
</div>