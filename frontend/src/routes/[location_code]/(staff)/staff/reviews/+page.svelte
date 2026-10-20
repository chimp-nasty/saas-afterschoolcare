<script lang="ts">
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import MedicalReviewTable from "$lib/features/medical-reviews/components/MedicalReviewTable.svelte";

    import { reviewTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    let activeTab = $state<string>(reviewTabs.PENDING);

    const tabs = $derived([
        { id: reviewTabs.PENDING, label: `Waiting (${data.pending.length})` },
        { id: reviewTabs.REQUESTED, label: `Requested (${data.requested.length})` }
    ]);
</script>

<Page width="wide">
    <PageHeader
        title="Medical reviews"
        description="Children with medical details can't be booked until staff approve them. Waiting: ready for staff to review. Requested: waiting on the family for documents. Longest waiting first."
    />

    <TabbedPanels
        {tabs}
        initialTab={reviewTabs.PENDING}
        bind:activeTab
        queryParam="state"
    >
        {#snippet panel(id)}
            {#if id === reviewTabs.PENDING}
                <MedicalReviewTable
                    reviews={data.pending}
                    locationCode={data.locationCode}
                    empty="No children are waiting for review."
                />
            {:else}
                <MedicalReviewTable
                    reviews={data.requested}
                    locationCode={data.locationCode}
                    empty="No families have been asked for documents."
                />
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>
