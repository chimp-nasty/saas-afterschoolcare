<!--
    The staff and admin navigation (a drawer on mobile). Links come in
    sections, each with an optional heading (e.g. "Families", "Settings");
    a section without one (Home, Logout, a family's links) has none shown.
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import Button from '../actions/Button.svelte';

	export type SidebarItem = {
		label: string;
		onclick: () => void;
		isActive?: boolean;
	};

	export type SidebarSection = {
		heading?: string;
		items: SidebarItem[];
	};

	let {
		sections,
		drawer = false
	}: {
		sections: SidebarSection[];
		drawer?: boolean;
	} = $props();
</script>

{#snippet nav()}
	<nav class="flex h-full flex-col gap-4 p-4">
		{#each sections.filter((section) => section.items.length > 0) as section, index (section.heading ?? index)}
			<div class="flex flex-col gap-2">
				<!-- Unlike the links (uppercase, muted): dark, bold, sentence case,
				     lined up with the links' text, with room above it. -->
				{#if section.heading}
					<p class="px-5 pt-2 text-sm font-extrabold text-(--text)">{section.heading}</p>
				{/if}

				{#each section.items as item (item.label)}
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
			</div>
		{/each}
	</nav>
{/snippet}

<div
	class={drawer
		? 'h-full'
		: 'h-full border-r border-(--border)'
	}
>
	{#if drawer}
		{@render nav()}
	{:else}
		<Card padded={false}>
			{@render nav()}
		</Card>
	{/if}
</div>
