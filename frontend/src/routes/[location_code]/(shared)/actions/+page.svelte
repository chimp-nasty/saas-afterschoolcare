<script lang="ts">
    import NewActions from "$lib/features/actions/components/NewActions.svelte";

    import TabbedPanels, {
        type TabConfig
    } from "$lib/components/controls/TabbedPanels.svelte";

    import { actionTabs } from "$lib/navigation/tabs";
    import { createActionsApi } from "$lib/api/public/adapters/actions";

    import type {
        ActionFilter,
        ActionResponse
    } from "$lib/api/public/types/actions";

    import type {
        Pagination,
        PaginationLoadMode
    } from "$lib/types/pagination";

    let { data } = $props();

    let activeTab = $state(actionTabs.NEW);
    let isLoading = $state(false);

    let uncitedActions: ActionResponse[] = $state([]);
    let citedActions: ActionResponse[] = $state([]);

    const actionsApi = createActionsApi();

    const tabs = $derived<TabConfig[]>([
        {
            id: actionTabs.NEW,
            label: "New",
            component: NewActions,
            props: {
                actions: uncitedActions,
                locationCode: data.locationCode,
                loader: loadActions,
                update: updateCited,
                isLoading
            }
        },
        {
            id: actionTabs.OLDER,
            label: "Older",
            component: null,
            props: {}
        }
    ]);

    async function loadActions(
        filters: ActionFilter,
        pagination: Pagination = {},
        mode: PaginationLoadMode = 'replace'
    ): Promise<number> {
        try {
            isLoading = true;

            const response = await actionsApi.list(
                filters,
                pagination
            );

            if (!response.ok || !response.data) {
                return 0;
            }

            const actions = response.data;

            if (filters.cited === true) {
                citedActions =
                    mode === 'append'
                        ? [...citedActions, ...actions]
                        : actions;
            } else {
                uncitedActions =
                    mode === 'append'
                        ? [...uncitedActions, ...actions]
                        : actions;
            }

            return actions.length;

        } finally {
            isLoading = false;
        }
    }

    async function updateCited(
        actionId: string
    ): Promise<void> {
        try {
            isLoading = true;

            await actionsApi.updateCitedAt(actionId);
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <TabbedPanels
        {tabs}
        bind:activeTab
        queryParam="state"
    />
</div>