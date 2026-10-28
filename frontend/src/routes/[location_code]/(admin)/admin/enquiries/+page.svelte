<!--
    Admin › Enquiries (docs/enquiries.md): messages from the centre page's
    contact form. Open (new and replied) first; open one to read it, reply
    by email, or close it.
-->
<script lang="ts">
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import EnquiryTable from "$lib/features/enquiries/components/EnquiryTable.svelte";

    import { enquiryTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    let activeTab = $state<string>(enquiryTabs.OPEN);

    const tabs = $derived([
        { id: enquiryTabs.OPEN, label: `Open (${data.open.length})` },
        { id: enquiryTabs.CLOSED, label: `Closed (${data.closed.length})` },
        { id: enquiryTabs.ALL, label: "All" }
    ]);
</script>

<Page width="wide">
    <PageHeader
        title="Enquiries"
        description="Messages from the contact form on your centre's page. Open: new and replied, newest first. Replies are emailed to the person, and their answers go to your centre's contact email."
    />

    <TabbedPanels {tabs} initialTab={enquiryTabs.OPEN} bind:activeTab queryParam="state">
        {#snippet panel(id)}
            {#if id === enquiryTabs.OPEN}
                <EnquiryTable enquiries={data.open} locationCode={data.locationCode} empty="No open enquiries." />
            {:else if id === enquiryTabs.CLOSED}
                <EnquiryTable enquiries={data.closed} locationCode={data.locationCode} empty="No closed enquiries." />
            {:else}
                <EnquiryTable enquiries={data.all} locationCode={data.locationCode} empty="No enquiries yet." />
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>
