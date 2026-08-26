<script lang="ts">
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';

	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Modal from '$lib/components/overlays/Modal.svelte';

	export type TabConfig = {
		id: string;
		label: string;
		component: any | null;
		props?: Record<string, unknown>;
	};

	let {
		tabs,
		initialTab,
		activeTab = $bindable(),
		queryParam
	}: {
		tabs: TabConfig[];
		initialTab?: string;
		activeTab?: string;
		queryParam?: string;
	} = $props();

	let modal = $state<any>(null);

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

		modal?.close();

		await updateUrl(tabId);
	}
</script>

<div class="flex flex-col gap-4">
	<div class="md:hidden">
		<Button
			type="button"
			variant="menu"
			fullWidth
			onclick={() => modal?.open()}
		>
			{activeTabLabel}
		</Button>
	</div>

	<div class="hidden flex-wrap md:flex">
		{#each tabs as tab}
			<Button
				type="button"
				variant="menu"
				isActive={activeTab === tab.id}
				onclick={() => selectTab(tab.id)}
			>
				{tab.label}
			</Button>
		{/each}
	</div>

	{#if activePanel?.component}
		{#key activePanel.id}
			<activePanel.component
				{...(activePanel.props ?? {})}
			/>
		{/key}
	{:else}
		<Card>
			<p class="p-4 text-sm text-(--text-muted)">
				This panel is not ready yet.
			</p>
		</Card>
	{/if}
</div>

<Modal bind:this={modal}>
	<div class="w-[min(28rem,calc(100vw-2rem))]">
		<div class="flex flex-col gap-4 p-4">
			{#each tabs as tab}
				<Button
					type="button"
					variant="menu"
					fullWidth
					isActive={activeTab === tab.id}
					onclick={() => selectTab(tab.id)}
				>
					{tab.label}
				</Button>
			{/each}

			<Button
				type="button"
				variant="ghost"
				fullWidth
				onclick={() => modal?.close()}
			>
				Close
			</Button>
		</div>
	</div>
</Modal>