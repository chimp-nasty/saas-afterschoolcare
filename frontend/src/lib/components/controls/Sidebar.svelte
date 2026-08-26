<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import HyperTextLink from '../actions/HyperTextLink.svelte';

	export type SidebarItem = {
		label: string;
		href: string;
	};

	let {
		items
	}: {
		items: SidebarItem[];
	} = $props();
</script>

<div class="h-full border-r border-(--border)">
	<Card>
		<nav class="flex h-full flex-col gap-2 p-4">
			{#each items as item}
				<HyperTextLink href={item.href}>
					{item.label}
				</HyperTextLink>
			{/each}
		</nav>
	</Card>
</div>