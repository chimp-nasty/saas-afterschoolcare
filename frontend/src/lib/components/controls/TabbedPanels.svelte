<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import type { Snippet } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';

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

	const defaultTabId = $derived(
		initialTab ?? tabs[0]?.id
	);

	const activePanel = $derived(
		tabs.find((tab) => tab.id === activeTab) ?? null
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

		await updateUrl(tabId);
	}
</script>

<div class="flex flex-col gap-4">
	<!-- Always inline: equal-width tabs on mobile, scrolling sideways if
	     they don't fit; fixed-width tabs from md. -->
	<div class="-mx-4 flex gap-2 overflow-x-auto px-4 md:mx-0 md:px-0">
		{#each tabs as tab (tab.id)}
			<div class="min-w-32 flex-1 shrink-0 md:w-40 md:flex-none">
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
