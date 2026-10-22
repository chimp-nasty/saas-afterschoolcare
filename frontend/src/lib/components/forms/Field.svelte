<script lang="ts">
	import type { Snippet } from 'svelte';

	import InlineError from './fields/InlineError.svelte';

	type Props = {
		label: string;
		error?: string | null;
		inline?: boolean;
		children: Snippet<[string]>;
	};

	let {
		label,
		error,
		inline = false,
		children
	}: Props = $props();

	const id = $props.id();
</script>

<div>
	{#if inline}
		<div class="flex items-center gap-2">
			{@render children(id)}

			<label for={id} class="field-label mb-0">
				{label}
			</label>
		</div>
	{:else}
		<label for={id} class="field-label">
			{label}
		</label>

		{@render children(id)}
	{/if}

	<InlineError message={error} />
</div>
