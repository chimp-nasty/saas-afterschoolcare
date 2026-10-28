<script lang="ts">
    import Button from "$lib/components/actions/Button.svelte";
    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import { invalidate, goto } from "$app/navigation";

    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Notice from "$lib/components/text/Notice.svelte";
    import CreateBookingFlow from "$lib/features/bookings/components/CreateBookingFlow.svelte";
    import { missingForBooking } from "$lib/features/customer/emergency";
    import { setupHref } from "$lib/features/customer/setup";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { CreateBookingRequest } from "$lib/api/schema";

    let { data } = $props();

    const bookingApi = createBookingApi();

    // Booking needs the parent's contact details and an emergency contact.
    const missing = $derived(data.profile ? missingForBooking(data.profile) : []);

    // "your phone number, your address and an emergency contact"
    function listed(items: string[]): string {
        return items.length > 1 ? `${items.slice(0, -1).join(", ")} and ${items.at(-1)}` : items[0];
    }

    async function handleConfirm(body: CreateBookingRequest) {
        const response = await bookingApi.create(body);

        // Pay on Stripe's hosted page; Stripe sends the user back to
        // /bookings/success, and its webhook confirms the bookings.
        if (response.ok && response.data?.checkout_url) {
            window.location.href = response.data.checkout_url;
        }

        // Refused (e.g. someone took the last place meanwhile): reload the
        // days so the calendar shows why.
        if (!response.ok) {
            await invalidate("app:new-booking");
        }

        return response;
    }
</script>

<Page>
    {#if !data.bookingsOpen}
        <PageHeader title="Book sessions" />

        <Notice tone="warning">
            {data.location.location_name} isn't taking bookings online yet. Please check back soon.
        </Notice>
    {:else if !missing.length}
        <CreateBookingFlow
            locationServices={data.locationServices}
            children={data.children}
            serviceDays={data.serviceDays}
            onConfirm={handleConfirm}
        />
    {:else}
        <PageHeader title="Book sessions" />

        <Notice tone="warning">Add {listed(missing)} before booking.</Notice>

        <ActionBar start>
            <Button variant="ghost" onclick={() => goto(setupHref(data.locationCode))}>Finish setting up</Button>
        </ActionBar>
    {/if}
</Page>
