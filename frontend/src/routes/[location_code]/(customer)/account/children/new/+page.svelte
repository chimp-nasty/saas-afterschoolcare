<script lang="ts">
    import { page } from "$app/state";
    import { goto, invalidate } from "$app/navigation";

    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import ChildProfileForm from "$lib/features/children/components/ChildProfileForm.svelte";
    import KioskPinModal from "$lib/features/customer/components/KioskPinModal.svelte";

    import { createChildrenApi } from "$lib/api/public/adapters/children";
    import type { CreateChildRequest } from "$lib/api/schema";
    import { accountTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    const childApi = createChildrenApi();

    let pinModal: KioskPinModal;

    function backToChildren() {
        void goto(`/${page.data.locationCode}/account?state=${accountTabs.CHILDREN}`);
    }

    // Back to Account → Children, where the new child now shows. Their
    // first child emails them a kiosk PIN: say so first.
    async function createChild(body: CreateChildRequest) {
        const response = await childApi.create(body);

        if (response.ok) {
            await invalidate("app:customer-account");

            if (data.isFirstChild) {
                pinModal.open();
            } else {
                backToChildren();
            }
        }

        return response;
    }
</script>

<KioskPinModal
    bind:this={pinModal}
    email={data.session?.email ?? null}
    centreName={data.location.location_name}
    onclose={backToChildren}
/>

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
