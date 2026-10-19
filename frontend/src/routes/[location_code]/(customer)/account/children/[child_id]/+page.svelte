<script lang="ts">
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { childTabs } from "$lib/navigation/tabs";

    let activeTab = $state<string>(childTabs.PROFILE);

    const tabs = [
        { id: childTabs.PROFILE, label: "Profile" },
        { id: childTabs.AUTHORIZED_PICKUPS, label: "Pickups" },
        { id: childTabs.MANAGE_DOCUMENTS, label: "Docs" }
    ];
</script>

<Page>
    <PageHeader title="Child details" />

    <TabbedPanels
        {tabs}
        initialTab={childTabs.PROFILE}
        bind:activeTab
        queryParam="state"
    >
        {#snippet panel()}
            <!-- None of the child panels are built yet. -->
            <Card>
                <p class="text-sm text-(--text-muted)">
                    This panel is not ready yet.
                </p>
            </Card>
        {/snippet}
    </TabbedPanels>
</Page>
