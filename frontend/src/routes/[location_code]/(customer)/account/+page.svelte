<script lang="ts">
    import Button from "$lib/components/actions/Button.svelte";
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";

    import ParentProfileForm from "$lib/features/customer/components/ParentProfileForm.svelte";
    import ChildAccountData from "$lib/features/children/components/ChildAccountData.svelte";
    import PickupList from "$lib/features/pickups/components/PickupList.svelte";

    import { invalidate } from "$app/navigation";

    import { accountTabs } from "$lib/navigation/tabs";
    import { logout } from "$lib/auth/logout";
	import { createCustomerApi } from "$lib/api/public/adapters/customer";
	import type { UpdateCustomerProfileRequest, CustomerProfileResponse } from "$lib/api/schema";

    let { data } = $props();

    let customerProfile = $derived<CustomerProfileResponse>(
        data.customerProfile
    );

    let activeTab = $state<string>(accountTabs.PROFILE);

    const customerApi = createCustomerApi();

    const tabs = [
        { id: accountTabs.PROFILE, label: "Profile" },
        { id: accountTabs.CHILDREN, label: "Children" },
        { id: accountTabs.PICKUPS, label: "Pickups" }
    ];

    async function updateProfile(
        body: UpdateCustomerProfileRequest
    ) {
        const response = await customerApi.updateProfile(body);

        if (response.ok && response.data) {
            customerProfile = response.data;

            // Their own pickup row follows their name and phone.
            await invalidate("app:customer-account");
        }

        return response;
    }
</script>

<Page>
    <PageHeader title="Account" />

    <TabbedPanels
        {tabs}
        bind:activeTab
        queryParam="state"
    >
        {#snippet panel(id)}
            {#if id === accountTabs.PROFILE}
                <ParentProfileForm
                    profile={customerProfile}
                    onsubmit={updateProfile}
                />
            {:else if id === accountTabs.CHILDREN}
                <ChildAccountData
                    locationCode={data.locationCode}
                    childProfiles={data.childProfiles}
                />
            {:else if id === accountTabs.PICKUPS}
                <PickupList
                    locationCode={data.locationCode}
                    pickups={data.pickups}
                />
            {/if}
        {/snippet}
    </TabbedPanels>

    <!-- Customers have no sidebar on mobile, so logging out lives here. -->
    <Button
        variant="ghost"
        fullWidth
        onclick={() => logout(data.locationCode)}
    >
        Log out
    </Button>
</Page>
