<!--
    Admin › Medical reviews: children waiting on staff, waiting on their
    family for documents, and approved (to reopen or ask for documents
    again), each searchable by the child's or the parent's name.
-->
<script lang="ts">
    import { goto } from "$app/navigation";
    import { page } from "$app/state";
    import { untrack } from "svelte";

    import Button from "$lib/components/actions/Button.svelte";
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import MedicalReviewTable from "$lib/features/medical-reviews/components/MedicalReviewTable.svelte";

    import { reviewTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    let activeTab = $state<string>(reviewTabs.PENDING);

    const tabs = $derived([
        { id: reviewTabs.PENDING, label: `Waiting (${data.pending.length})` },
        { id: reviewTabs.REQUESTED, label: `Requested (${data.requested.length})` },
        { id: reviewTabs.APPROVED, label: `Approved (${data.approved.length})` }
    ]);

    // Starts as what was searched (the page reloads with each search).
    let text = $state(untrack(() => data.q));

    // Searches every list, staying on the current tab; an empty search clears it.
    function search(event: SubmitEvent) {
        event.preventDefault();

        const params: Record<string, string> = { state: page.url.searchParams.get("state") ?? activeTab };

        if (text.trim()) params.q = text.trim();

        void goto(`?${new URLSearchParams(params)}`, { keepFocus: true, noScroll: true });
    }
</script>

<Page width="wide">
    <PageHeader
        title="Medical reviews"
        description="Children with medical details can't be booked until an admin approves them. Waiting: ready for you to review. Requested: waiting on the family for documents (longest waiting first). Approved: newest first; open one to reopen it or ask for documents again."
    />

    <form class="flex flex-wrap items-end gap-3" onsubmit={search}>
        <label class="flex min-w-72 flex-1 flex-col gap-1">
            <span class="label-text">Child or parent name</span>
            <input type="search" autocomplete="off" bind:value={text} />
        </label>
        <Button type="submit" isDisabled={text.trim().length === 1}>Search</Button>
    </form>

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
            {:else if id === reviewTabs.REQUESTED}
                <MedicalReviewTable
                    reviews={data.requested}
                    locationCode={data.locationCode}
                    empty="No families have been asked for documents."
                />
            {:else}
                <MedicalReviewTable
                    reviews={data.approved}
                    locationCode={data.locationCode}
                    empty={data.q ? `No approved children match "${data.q}".` : "No children have been approved yet."}
                    approved
                />
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>
