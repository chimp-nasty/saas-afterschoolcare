<script lang="ts">
    import TabbedPanels, { type TabConfig } from "$lib/components/controls/TabbedPanels.svelte";

    import ParentProfileForm from "$lib/features/customer/components/ParentProfileForm.svelte";
    import ChildAccountData from "$lib/features/customer/components/ChildAccountData.svelte";

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

    let activeTab = $state("parent-details");

    let isLoading: boolean = $state(false);

    const tabs = $derived<TabConfig[]>([
        {
            id: "parent-details",
            label: "Parent",
            component: ParentProfileForm,
            props: {
                profile: customerProfile,
                handleSubmit: updateProfile,
                isLoading
            }
        },
        {
            id: "children",
            label: "Children",
            component: ChildAccountData,
            props: {
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
        initialTab="parent-details"
        bind:activeTab
        queryParam="state"
    />
</div>