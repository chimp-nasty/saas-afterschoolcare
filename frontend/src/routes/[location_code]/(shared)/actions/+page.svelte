<script lang="ts">
    import NewActions from "$lib/features/actions/components/NewActions.svelte";

    import TabbedPanels, {
        type TabConfig
    } from "$lib/components/controls/TabbedPanels.svelte";

    import { actionTabs } from "$lib/navigation/tabs";
    import { createActionsApi } from "$lib/api/public/adapters/actions";

    let { data } = $props();

    let activeTab = $state(actionTabs.NEW);
    let isLoading = $state(false);

    const actionsApi = createActionsApi();

    const tabs = $derived<TabConfig[]>([
        {
            id: actionTabs.NEW,
            label: "New",
            component: NewActions,
            props: {
                actions: data.actions,
                locationCode: data.locationCode
            }
        },
        {
            id: actionTabs.OLDER,
            label: "Older",
            component: null,
            props: {}
        }
    ]);
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <TabbedPanels
        {tabs}
        bind:activeTab
        queryParam="state"
    />
</div>