<script lang="ts">
    import { goto, invalidate } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";
    import EditChildProfileForm from "$lib/features/children/components/EditChildProfileForm.svelte";

    import { createChildrenApi } from "$lib/api/public/adapters/children";
    import type { ChildResponse, UpdateChildRequest } from "$lib/api/schema";
    import { accountTabs, childTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    const childrenApi = createChildrenApi();

    // Starts from the loader; a save replaces it with what the server
    // returns (including a review status the change may have reset).
    let child = $derived<ChildResponse>(data.child);

    let activeTab = $state<string>(childTabs.PROFILE);

    const tabs = [
        { id: childTabs.PROFILE, label: "Profile" },
        { id: childTabs.MANAGE_DOCUMENTS, label: "Docs" }
    ];

    const REVIEW_NOTICES: Partial<Record<ChildResponse["review_status"], string>> = {
        pending: "Staff are reviewing this child's medical details. They can't be booked until it's approved.",
        documentation_requested: "Staff need documents for this child's medical details before they can be booked.",
    };

    async function updateChild(body: UpdateChildRequest) {
        const response = await childrenApi.update(child.id, body);

        if (response.ok && response.data) {
            child = response.data;
        }

        return response;
    }

    let removeModal: Modal;
    let isRemoving = $state(false);

    // Refused (and explained in a toast) while the child has upcoming
    // bookings.
    async function removeChild() {
        isRemoving = true;

        try {
            const response = await childrenApi.deactivate(child.id);

            if (response.ok) {
                await invalidate("app:customer-account");
                await goto(`/${data.locationCode}/account?state=${accountTabs.CHILDREN}`);
                return;
            }

            removeModal.close();
        } finally {
            isRemoving = false;
        }
    }
</script>

<Page>
    <PageHeader title={`${child.first_name} ${child.last_name}`} />

    <TabbedPanels
        {tabs}
        initialTab={childTabs.PROFILE}
        bind:activeTab
        queryParam="state"
    >
        {#snippet panel(id)}
            {#if id === childTabs.PROFILE}
                {@const notice = REVIEW_NOTICES[child.review_status]}

                {#if notice}
                    <Card border>
                        <p class="text-sm text-(--text-muted)">
                            {notice}
                        </p>
                    </Card>
                {/if}

                <EditChildProfileForm
                    {child}
                    onsubmit={updateChild}
                />

                <Button
                    variant="ghost"
                    fullWidth
                    onclick={() => removeModal.open()}
                >
                    Remove child
                </Button>
            {:else}
                <!-- Documents aren't built yet. -->
                <Card>
                    <p class="text-sm text-(--text-muted)">
                        This panel is not ready yet.
                    </p>
                </Card>
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>

<Modal bind:this={removeModal} title={`Remove ${child.first_name}?`}>
    <p class="text-sm text-(--text-muted)">
        {child.first_name} will no longer appear in your account and can't be
        booked. Past bookings are kept. You can't remove a child with upcoming
        bookings.
    </p>

    {#snippet actions()}
        <Button variant="ghost" onclick={() => removeModal.close()}>
            Keep
        </Button>

        <Button onclick={removeChild} isLoading={isRemoving}>
            Remove child
        </Button>
    {/snippet}
</Modal>
