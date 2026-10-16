<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import type { Snippet } from 'svelte';
	import { ChevronRight } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Drawer from '$lib/components/overlays/Drawer.svelte';

	export type Tab = {
		id: string;
		label: string;
	};

	let {
		tabs,
		initialTab,
		activeTab = $bindable(),
		queryParam,
		panel
	}: {
		tabs: Tab[];
		initialTab?: string;
		activeTab?: string;
		queryParam?: string;
		// Rendered with the active tab id; remounts when the tab changes.
		panel: Snippet<[string]>;
	} = $props();

	let drawerOpen = $state(false);

	const defaultTabId = $derived(
		initialTab ?? tabs[0]?.id
	);

	const activePanel = $derived(
		tabs.find((tab) => tab.id === activeTab) ?? null
	);

	const activeTabLabel = $derived(
		activePanel?.label ?? 'Select section'
	);

	function isValidTab(tabId: string | null | undefined) {
		return Boolean(
			tabId &&
			tabs.some((tab) => tab.id === tabId)
		);
	}

	$effect(() => {
		const queryTab = queryParam
			? page.url.searchParams.get(queryParam)
			: null;

		if (isValidTab(queryTab)) {
			activeTab = queryTab!;
			return;
		}

		if (!isValidTab(activeTab)) {
			activeTab = defaultTabId;
		}
	});

	async function updateUrl(tabId: string) {
		if (!browser || !queryParam) return;

		const url = new URL(page.url);

		url.searchParams.set(
			queryParam,
			tabId
		);

		await goto(
			`${url.pathname}${url.search}${url.hash}`,
			{
				replaceState: true,
				noScroll: true,
				keepFocus: true
			}
		);
	}

	async function selectTab(tabId: string) {
		activeTab = tabId;
		drawerOpen = false;

		await updateUrl(tabId);
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Mobile tab selector -->
	<div class="md:hidden">
		<Button
			type="button"
			variant="menu"
			fullWidth
			onclick={() => drawerOpen = true}
		>
			<span class="flex w-full items-center justify-between">
				<span>
					{activeTabLabel}
				</span>

				<ChevronRight size={18} />
			</span>
		</Button>
	</div>

	<!-- Desktop tabs -->
	<div class="hidden flex-wrap gap-2 md:flex">
		{#each tabs as tab}
			<div class="w-40">
				<Button
					type="button"
					variant="menu"
					fullWidth
					isActive={activeTab === tab.id}
					onclick={() => selectTab(tab.id)}
				>
					{tab.label}
				</Button>
			</div>
		{/each}
	</div>

	<!-- Active panel -->
	{#if activePanel}
		{#key activePanel.id}
			{@render panel(activePanel.id)}
		{/key}
	{/if}
</div>

<Drawer
	open={drawerOpen}
	onclose={() => drawerOpen = false}
>
	<div class="flex flex-col gap-2 p-4">
		{#each tabs as tab}
			<Button
				type="button"
				variant="menu"
				fullWidth
				isActive={activeTab === tab.id}
				onclick={() => selectTab(tab.id)}
			>
				<span class="flex w-full items-center justify-between">
					<span>{tab.label}</span>

					{#if activeTab === tab.id}
						<span class="text-xs text-(--primary)">
							Selected
						</span>
					{/if}
				</span>
			</Button>
		{/each}
	</div>
</Drawer>