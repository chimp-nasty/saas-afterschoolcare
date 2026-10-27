<!--
    Stripe sends the user here after checkout (?session_id=...). Loading the
    status checks the payment with Stripe, so a paid card booking usually
    shows as confirmed at once; a slower payment (or Stripe unreachable)
    stays pending, so poll briefly.
-->
<script lang="ts">
    import { goto } from "$app/navigation";
    import Button from "$lib/components/actions/Button.svelte";
    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import { onMount } from "svelte";
    import { page } from "$app/state";

    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { CheckoutStatusResponse } from "$lib/api/schema";
    import { BOOKING_STATUS_LABELS } from "$lib/features/bookings/status";
    import { formatDate, formatMoney } from "$lib/utils/helpers";

    let { data } = $props();

    const POLL_ATTEMPTS = 10;
    const POLL_INTERVAL_MS = 2000;

    const bookingApi = createBookingApi();

    let checkout = $state<CheckoutStatusResponse | null>(null);
    let error = $state<string | null>(null);

    const sessionId = page.url.searchParams.get("session_id");

    // What the header says for each state of the checkout.
    const result = $derived.by((): { title: string; description: string } => {
        if (error) {
            return { title: "We couldn't find this checkout", description: error };
        }

        if (!checkout || checkout.payment_status === "PENDING") {
            return {
                title: "Confirming your payment…",
                description:
                    "This usually takes a few seconds. You can leave this page; your bookings will update once payment is confirmed.",
            };
        }

        if (checkout.payment_status === "SUCCEEDED") {
            return {
                title: "Booking confirmed",
                description: `Paid ${formatMoney(checkout.total_cents, checkout.currency)}.`,
            };
        }

        return {
            title: "Payment didn't go through",
            description: "These dates have been released. You can start a new booking.",
        };
    });

    onMount(() => {
        let cancelled = false;

        async function poll() {
            if (!sessionId) {
                error = "Missing checkout reference.";
                return;
            }

            for (let attempt = 0; attempt < POLL_ATTEMPTS && !cancelled; attempt++) {
                const response = await bookingApi.getCheckoutStatus(sessionId);

                if (!response.ok || !response.data) {
                    error = response.msg;
                    return;
                }

                checkout = response.data;

                if (checkout.payment_status !== "PENDING") {
                    return;
                }

                await new Promise((resolve) => setTimeout(resolve, POLL_INTERVAL_MS));
            }
        }

        void poll();

        return () => {
            cancelled = true;
        };
    });
</script>

<Page>
    <PageHeader title={result.title} description={result.description} />

    {#if checkout}
        <div class="flex flex-col gap-4">
            {#each checkout.bookings as booking (booking.id)}
                <DataCard
                    title={booking.child_name}
                    data={[
                        { label: "Service", value: booking.service_name },
                        { label: "Date", value: formatDate(booking.service_date) },
                        { label: "Status", value: BOOKING_STATUS_LABELS[booking.booking_status] },
                    ]}
                />
            {/each}
        </div>
    {/if}

    <ActionBar start>
        <Button variant="ghost" onclick={() => goto(`/${data.locationCode}/bookings`)}>View all bookings</Button>
    </ActionBar>
</Page>
