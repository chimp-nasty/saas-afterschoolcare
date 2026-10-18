<!--
    Review a pending booking group: continue to Stripe, or cancel it and
    release the places. Other statuses just explain where the booking is.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";

    import Card from "$lib/components/layout/Card.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";
    import ReviewBooking, { type ReviewChild } from "$lib/features/bookings/components/ReviewBooking.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";

    let { data } = $props();

    const bookingApi = createBookingApi();

    const group = $derived(data.group);

    // One section per child, in the order their bookings come back (by date).
    const reviewChildren = $derived.by((): ReviewChild[] => {
        const byChild = new Map<string, ReviewChild>();

        for (const booking of group.bookings) {
            const child = byChild.get(booking.child_id) ?? {
                childId: booking.child_id,
                childName: booking.child_name,
                lines: [],
            };

            child.lines.push({
                date: booking.service_date,
                serviceName: booking.service_name,
                priceCents: booking.price_snapshot_cents,
            });

            byChild.set(booking.child_id, child);
        }

        return [...byChild.values()];
    });

    const STATUS_MESSAGES: Record<string, { title: string; body: string }> = {
        CONFIRMED: {
            title: "Booking confirmed",
            body: "This booking is paid in full.",
        },
        EXPIRED: {
            title: "This booking has expired",
            body: "It wasn't paid in time, so the places were released. You can make a new booking.",
        },
        CANCELLED: {
            title: "This booking was cancelled",
            body: "The places were released. You can make a new booking.",
        },
    };

    let isPaying = $state(false);
    let isCancelling = $state(false);

    async function continueToPayment() {
        isPaying = true;

        try {
            const response = await bookingApi.createGroupCheckout(group.booking_group_id);

            if (response.ok && response.data) {
                window.location.href = response.data.checkout_url;
                return;
            }

            // Expired or paid in the meantime: show its current state.
            await invalidate("app:booking-group");
        } finally {
            isPaying = false;
        }
    }

    async function cancelBooking() {
        if (!window.confirm("Cancel this booking and release the places?")) {
            return;
        }

        isCancelling = true;

        try {
            const response = await bookingApi.cancelGroup(group.booking_group_id);

            if (response.ok) {
                await invalidate("app:home-bookings");
                await goto(`/${data.locationCode}/home`);
                return;
            }

            await invalidate("app:booking-group");
        } finally {
            isCancelling = false;
        }
    }
</script>

<div class="mx-auto w-full max-w-5xl">
    <div class="mb-8">
        <h1 class="text-2xl font-semibold text-gray-900">
            {group.status === "PENDING" ? "Review your booking" : "Your booking"}
        </h1>
    </div>

    {#if group.status !== "PENDING"}
        {@const message = STATUS_MESSAGES[group.status]}

        <div class="mb-6">
            <Card border>
                <div class="p-5">
                    <h2 class="text-lg font-extrabold text-(--text)">
                        {message?.title ?? "This booking can't be changed"}
                    </h2>

                    <p class="mt-1 text-sm text-(--text-muted)">
                        {message?.body ?? ""}
                    </p>
                </div>
            </Card>
        </div>
    {/if}

    <ReviewBooking
        serviceName={group.bookings[0]?.service_name ?? "Booking"}
        currency={group.currency}
        children={reviewChildren}
    >
        {#snippet actions()}
            {#if group.status === "PENDING"}
                <button
                    type="button"
                    onclick={cancelBooking}
                    disabled={isCancelling || isPaying}
                    class="rounded-lg border border-gray-300 px-5 py-2.5 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
                >
                    {isCancelling ? "Cancelling…" : "Cancel booking"}
                </button>

                <button
                    type="button"
                    onclick={continueToPayment}
                    disabled={isPaying || isCancelling}
                    class="rounded-lg bg-gray-900 px-5 py-2.5 font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                    {isPaying ? "Opening checkout…" : "Continue to payment"}
                </button>
            {:else}
                <HyperTextLink href={`/${data.locationCode}/bookings`}>
                    Back to my bookings
                </HyperTextLink>
            {/if}
        {/snippet}
    </ReviewBooking>
</div>
