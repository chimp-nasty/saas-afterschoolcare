<script lang="ts">
    import { invalidate } from "$app/navigation";

    import Page from "$lib/components/layout/Page.svelte";
    import CreateBookingFlow from "$lib/features/bookings/components/CreateBookingFlow.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { CreateBookingRequest } from "$lib/api/schema";

    let { data } = $props();

    const bookingApi = createBookingApi();

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
    <CreateBookingFlow
        locationServices={data.locationServices}
        children={data.children}
        serviceDays={data.serviceDays}
        onConfirm={handleConfirm}
    />
</Page>
