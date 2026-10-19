<!--
    Tabs and the active tab's panel. Up to 3 tabs show inline as equal-width
    tabs that shrink to fit (labels may wrap), so there's never a sideways
    scroll. With more than 3, mobile gets a native select instead (the phone's
    own picker) and desktop keeps the inline tabs.
-->
<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import type { Snippet } from 'svelte';

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

	const MAX_INLINE_TABS = 3;

	const useSelectOnMobile = $derived(tabs.length > MAX_INLINE_TABS);

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
	{#if useSelectOnMobile}
		<select
			class="md:hidden"
			aria-label="Section"
			value={activeTab}
			onchange={(event) => selectTab(event.currentTarget.value)}
		>
			{#each tabs as tab (tab.id)}
				<option value={tab.id}>{tab.label}</option>
			{/each}
		</select>
	{/if}

	<div
		role="tablist"
		class={['gap-2 md:flex', useSelectOnMobile ? 'hidden' : 'grid']}
		style:grid-template-columns={`repeat(${tabs.length}, minmax(0, 1fr))`}
	>
		{#each tabs as tab (tab.id)}
			<button
				type="button"
				role="tab"
				aria-selected={activeTab === tab.id}
				onclick={() => selectTab(tab.id)}
				class={[
					'flex min-h-12 w-full items-center justify-center border-y px-2 py-2 text-center text-xs font-extrabold uppercase tracking-wider transition md:w-40',
					activeTab === tab.id
						? 'border-(--primary) bg-(--primary-soft) text-(--primary)'
						: 'border-(--border) text-(--text-muted) hover:bg-(--primary-soft) hover:text-(--primary)'
				]}
			>
				{tab.label}
			</button>
		{/each}
	</div>

	<!-- Active panel -->
	{#if activePanel}
		{#key activePanel.id}
			{@render panel(activePanel.id)}
		{/key}
	{/if}
</div>
