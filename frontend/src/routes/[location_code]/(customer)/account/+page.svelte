<script lang="ts">
    import TabbedPanels, { type TabConfig } from "$lib/components/controls/TabbedPanels.svelte";

    import ParentProfileForm from "$lib/features/customer/components/ParentProfileForm.svelte";
    import ChildAccountData from "$lib/features/children/components/ChildAccountData.svelte";

    import { accountTabs } from "$lib/navigation/tabs.js";
	import { createCustomerApi } from "$lib/api/public/adapters/customer";
	import type { UpdateCustomerProfileRequest, CustomerProfileResponse } from "$lib/api/public/types/customer";
    import type { ChildTableResponse } from "$lib/api/public/types/children.js";

    let { data } = $props();

    let customerProfile = $derived<CustomerProfileResponse>(
        data.customerProfile
    );
    
    let childProfiles = $derived<ChildTableResponse[]>(
        data.childProfiles
    );

    let activeTab = $state(accountTabs.PROFILE);

    let isLoading: boolean = $state(false);

    const tabs = $derived<TabConfig[]>([
        {
            id: accountTabs.PROFILE,
            label: "Parent Profile",
            component: ParentProfileForm,
            props: {
                profile: customerProfile,
                handleSubmit: updateProfile,
                isLoading
            }
        },
        {
            id: accountTabs.CHILDREN,
            label: "Children",
            component: ChildAccountData,
            props: {
                locationCode: data.locationCode,
                childProfiles
            }
        }
    ]);
    
    async function updateProfile(
        body: UpdateCustomerProfileRequest
    ) {
        const customerApi = createCustomerApi();
        try {
            isLoading = true;

            const response = await customerApi.updateProfile(body);

            if (!response.ok || !response.data) return;

            customerProfile = response.data;
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <TabbedPanels
        {tabs}
        bind:activeTab
        queryParam="state"
    />
</div>