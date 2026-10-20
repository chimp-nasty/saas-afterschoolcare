<script lang="ts">
    import { page } from "$app/state";
    import { goto, invalidate } from "$app/navigation";

    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import PickupForm, { type PickupFormValues } from "$lib/features/pickups/components/PickupForm.svelte";

    import { createPickupsApi } from "$lib/api/public/adapters/pickups";
    import { accountTabs } from "$lib/navigation/tabs";

    const pickupsApi = createPickupsApi();

    // The declaration boxes are required in the form, so they're ticked.
    async function addPickup(values: PickupFormValues) {
        const response = await pickupsApi.create({
            ...values,
            consent_confirmed: true,
            adult_confirmed: true,
        });

        if (response.ok) {
            await invalidate("app:customer-account");
            await goto(`/${page.data.locationCode}/account?state=${accountTabs.PICKUPS}`);
        }

        return response;
    }
</script>

<Page>
    <PageHeader
        title="Add a pickup person"
        description="They'll be able to collect all of your children."
    />

    <PickupForm onsubmit={addPickup} />

    <Card border>
        <p class="text-sm text-(--text-muted)">
            We'll email them a kiosk PIN, which they'll change the first time
            they sign in at the centre. Staff check their photo ID before they
            can collect.
        </p>
    </Card>
</Page>
