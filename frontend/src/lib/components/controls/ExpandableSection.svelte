<!--
    A section that opens and closes: a full-width 44px toggle row with the
    title as a label, optional actions beside it, and the content below.
-->
<script lang="ts">
	import { untrack, type Snippet } from 'svelte';
	import { ChevronDown } from 'lucide-svelte';

	let {
		title,
		defaultOpen = false,
		children,
		actions
	}: {
		title: string;
		defaultOpen?: boolean;
		children?: Snippet;
		actions?: Snippet;
	} = $props();

	// Starts from defaultOpen; after that only the toggle changes it.
	let isOpen = $state(untrack(() => defaultOpen));

	const contentId = $props.id();
</script>

<div class="flex flex-col gap-2">
	<div class="flex items-center justify-between gap-2">
		<button
			type="button"
			aria-expanded={isOpen}
			aria-controls={contentId}
			onclick={() => (isOpen = !isOpen)}
			class="flex min-h-11 flex-1 items-center justify-between gap-2 text-left label-text"
		>
			{title}

			<ChevronDown
				size={18}
				class={`shrink-0 transition-transform ${isOpen ? 'rotate-180' : ''}`}
			/>
		</button>

		{@render actions?.()}
	</div>

	{#if isOpen}
		<div id={contentId}>
			{@render children?.()}
		</div>
	{/if}
</div>
