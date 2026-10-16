<script lang="ts">
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import { childTabs } from "$lib/navigation/tabs";

    let activeTab = $state<string>(childTabs.PROFILE);

    const tabs = [
        { id: childTabs.PROFILE, label: "Profile" },
        { id: childTabs.AUTHORIZED_PICKUPS, label: "Authorized Pickups" },
        { id: childTabs.MANAGE_DOCUMENTS, label: "Manage Documents" }
    ];
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <TabbedPanels
        {tabs}
        initialTab={childTabs.PROFILE}
        bind:activeTab
        queryParam="state"
    >
        {#snippet panel()}
            <!-- None of the child panels are built yet. -->
            <Card>
                <p class="p-4 text-sm text-(--text-muted)">
                    This panel is not ready yet.
                </p>
            </Card>
        {/snippet}
    </TabbedPanels>
</div>
