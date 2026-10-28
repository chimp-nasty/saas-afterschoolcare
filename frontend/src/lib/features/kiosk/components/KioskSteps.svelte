<!--
    Where a parent is up to at the family kiosk: Mobile → PIN → Your
    children. Done steps are ticked, the current one is highlighted.
-->
<script lang="ts">
	import { Check } from 'lucide-svelte';

	let { current }: { current: 0 | 1 | 2 } = $props();

	const STEPS = ['Mobile', 'PIN', 'Your children'];
</script>

<ol class="flex flex-wrap items-center justify-center gap-3" aria-label="Steps">
	{#each STEPS as label, index (label)}
		{#if index > 0}
			<li class="h-0.5 w-8 rounded-full bg-(--border)" aria-hidden="true"></li>
		{/if}

		<li
			class={[
				'flex items-center gap-2 text-lg font-semibold',
				index === current ? 'text-(--primary)' : index < current ? 'text-(--text)' : 'text-(--text-muted)'
			]}
			aria-current={index === current ? 'step' : undefined}
		>
			<span
				class={[
					'flex size-8 items-center justify-center rounded-full border-2 text-base font-extrabold',
					index < current
						? 'border-(--primary) bg-(--primary) text-white'
						: index === current
							? 'border-(--primary) text-(--primary)'
							: 'border-(--border)'
				]}
				aria-hidden="true"
			>
				{#if index < current}
					<Check size={18} strokeWidth={3} />
				{:else}
					{index + 1}
				{/if}
			</span>

			{label}
		</li>
	{/each}
</ol>
