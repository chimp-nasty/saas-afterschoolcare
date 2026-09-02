<script lang="ts">
    import TabbedPanels, { type TabConfig } from "$lib/components/controls/TabbedPanels.svelte";

    import type { PageData } from "./$types";

    let { data }: { data: PageData } = $props();

    let activeTab = $state("parent-details");

    const tabs = $derived<TabConfig[]>([
        {
            id: "parent-details",
            label: "Parent",
            component: null,
            props: {

            }
        },
        {
            id: "children",
            label: "Children",
            component: null,
            props: {

            }
        }
    ]);
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <TabbedPanels
        {tabs}
        initialTab="parent-details"
        bind:activeTab
        queryParam="state"
    />
</div>