<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import Button from '../actions/Button.svelte';

	export type SidebarItem = {
		label: string;
		onclick: () => void;
		isActive?: boolean;
	};

	let {
		items,
		drawer = false
	}: {
		items: SidebarItem[];
		drawer?: boolean;
	} = $props();
</script>

<div
	class={drawer
		? 'h-full'
		: 'h-full border-r border-(--border)'
	}
>
	{#if drawer}
		<nav class="flex h-full flex-col gap-2 p-4">
			{#each items as item}
				<Button
					variant="menu"
					fullWidth
					isActive={item.isActive}
					onclick={item.onclick}
				>
					<span class="flex w-full items-center justify-between">
						<span>
							{item.label}
						</span>

						{#if item.isActive}
							<span class="text-xs text-(--primary)">
								Selected
							</span>
						{/if}
					</span>
				</Button>
			{/each}
		</nav>
	{:else}
		<Card>
			<nav class="flex h-full flex-col gap-2 p-4">
				{#each items as item}
					<Button
						variant="menu"
						fullWidth
						isActive={item.isActive}
						onclick={item.onclick}
					>
						<span class="flex w-full items-center justify-between">
							<span>
								{item.label}
							</span>

							{#if item.isActive}
								<span class="text-xs text-(--primary)">
									Selected
								</span>
							{/if}
						</span>
					</Button>
				{/each}
			</nav>
		</Card>
	{/if}
</div>