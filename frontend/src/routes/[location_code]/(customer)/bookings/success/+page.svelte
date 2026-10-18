<!--
    Stripe sends the user here after checkout (?session_id=...). This page
    only shows the result: the Stripe webhook is what confirms the bookings,
    and it can land a few seconds after the redirect, so poll briefly.
-->
<script lang="ts">
    import { onMount } from "svelte";
    import { page } from "$app/state";

    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { CheckoutStatusResponse } from "$lib/api/schema";

    let { data } = $props();

    const POLL_ATTEMPTS = 10;
    const POLL_INTERVAL_MS = 2000;

    const bookingApi = createBookingApi();

    let checkout = $state<CheckoutStatusResponse | null>(null);
    let error = $state<string | null>(null);

    const sessionId = page.url.searchParams.get("session_id");

    function formatPrice(cents: number, currency: string): string {
        return new Intl.NumberFormat("en-AU", {
            style: "currency",
            currency,
        }).format(cents / 100);
    }

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

<div class="flex w-full max-w-xl flex-1 flex-col gap-4">
    <Card border>
        <div class="p-5">
            {#if error}
                <h1 class="text-lg font-extrabold text-(--danger-text)">
                    We couldn't find this checkout
                </h1>
                <p class="mt-1 text-sm text-(--text-muted)">{error}</p>
            {:else if !checkout || checkout.payment_status === "PENDING"}
                <h1 class="text-lg font-extrabold text-(--text)">
                    Confirming your payment…
                </h1>
                <p class="mt-1 text-sm text-(--text-muted)">
                    This usually takes a few seconds. You can leave this page; your
                    bookings will update once payment is confirmed.
                </p>
            {:else if checkout.payment_status === "SUCCEEDED"}
                <h1 class="text-lg font-extrabold text-(--success-text)">
                    Booking confirmed
                </h1>
                <p class="mt-1 text-sm text-(--text-muted)">
                    Paid {formatPrice(checkout.total_cents, checkout.currency)}.
                </p>
            {:else}
                <h1 class="text-lg font-extrabold text-(--danger-text)">
                    Payment didn't go through
                </h1>
                <p class="mt-1 text-sm text-(--text-muted)">
                    These dates have been released. You can start a new booking.
                </p>
            {/if}
        </div>
    </Card>

    {#if checkout}
        {#each checkout.bookings as booking (booking.id)}
            <DataCard
                title={booking.child_name}
                data={[
                    { label: "Service", value: booking.service_name },
                    { label: "Date", value: booking.service_date, format: "date" },
                    { label: "Status", value: booking.booking_status, format: "enum" },
                ]}
            />
        {/each}
    {/if}

    <HyperTextLink href={`/${data.locationCode}/bookings`}>
        View all bookings
    </HyperTextLink>
</div>
