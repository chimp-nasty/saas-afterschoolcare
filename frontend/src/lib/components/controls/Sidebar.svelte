<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import HyperTextLink from '../actions/HyperTextLink.svelte';
	import Button from '../actions/Button.svelte';

	export type SidebarItem = {
		label: string;
		href?: string;
		onclick?: () => void;
	};

	let {
		items
	}: {
		items: SidebarItem[];
	} = $props();
</script>

<div class="h-full border-r border-(--border)">
	<Card>
		<nav class="flex h-full flex-col px-5 py-1">
			{#each items as item, index}
				<div
					class={`
						border-y border-(--border)
						px-1 py-4
						${index > 0 ? '-mt-px' : ''}
					`}
				>
					{#if item.href}
						<HyperTextLink href={item.href}>
							{item.label}
						</HyperTextLink>
					{:else if item.onclick}
						<Button
							variant="hyperlink"
							onclick={item.onclick}
						>
							{item.label}
						</Button>
					{/if}
				</div>
			{/each}
		</nav>
	</Card>
</div>