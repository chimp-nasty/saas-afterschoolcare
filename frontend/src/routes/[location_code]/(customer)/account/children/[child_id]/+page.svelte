<script lang="ts">
    import TabbedPanels, { type TabConfig } from "$lib/components/controls/TabbedPanels.svelte";
    import { childTabs } from "$lib/navigation/tabs";

    let activeTab = $state("profile");

    let isLoading: boolean = $state(false);

    const tabs = $derived<TabConfig[]>([
        {
            id: childTabs.PROFILE,
            label: "Profile",
            component: null,
            props: {
                isLoading
            }
        },
        {
            id: childTabs.AUTHORIZED_PICKUPS,
            label: "Authorized Pickups",
            component: null,
            props: {
                isLoading
            }
        },
        {
            id: childTabs.MANAGE_DOCUMENTS,
            label: "Manage Documents",
            component: null,
            props: {
                isLoading
            }
        }
    ]);
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <TabbedPanels
        {tabs}
        initialTab="profile"
        bind:activeTab
        queryParam="state"
    />
</div>