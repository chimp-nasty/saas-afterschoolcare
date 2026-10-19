<script lang="ts">
    import { page } from "$app/state";
    import { goto, invalidate } from "$app/navigation";

    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import ChildProfileForm from "$lib/features/children/components/ChildProfileForm.svelte";

    import { createChildrenApi } from "$lib/api/public/adapters/children";
    import type { CreateChildRequest } from "$lib/api/schema";
    import { accountTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    const childApi = createChildrenApi();

    // Back to Account → Children, where the new child now shows.
    async function createChild(body: CreateChildRequest) {
        const response = await childApi.create(body);

        if (response.ok) {
            await invalidate("app:customer-account");
            await goto(`/${page.data.locationCode}/account?state=${accountTabs.CHILDREN}`);
        }

        return response;
    }
</script>

<Page>
    <PageHeader
        title="Add a child"
        description="Children with medical conditions, allergies or medication are reviewed by staff before they can be booked."
    />

    <ChildProfileForm
        askPickupConsent={data.hasOtherPickups}
        onsubmit={createChild}
    />
</Page>
