<script lang="ts">
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";

    import ParentProfileForm from "$lib/features/customer/components/ParentProfileForm.svelte";
    import ChildAccountData from "$lib/features/children/components/ChildAccountData.svelte";

    import { accountTabs } from "$lib/navigation/tabs";
	import { createCustomerApi } from "$lib/api/public/adapters/customer";
	import type { UpdateCustomerProfileRequest, CustomerProfileResponse } from "$lib/api/schema";

    let { data } = $props();

    let customerProfile = $derived<CustomerProfileResponse>(
        data.customerProfile
    );

    let activeTab = $state<string>(accountTabs.PROFILE);

    const customerApi = createCustomerApi();

    const tabs = [
        { id: accountTabs.PROFILE, label: "Parent Profile" },
        { id: accountTabs.CHILDREN, label: "Children" }
    ];

    async function updateProfile(
        body: UpdateCustomerProfileRequest
    ) {
        const response = await customerApi.updateProfile(body);

        if (response.ok && response.data) {
            customerProfile = response.data;
        }

        return response;
    }
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
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
            {/if}
        {/snippet}
    </TabbedPanels>
</div>
