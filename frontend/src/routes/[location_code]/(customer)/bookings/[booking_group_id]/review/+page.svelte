<!--
    Review a booking group. Pending: continue to Stripe, or cancel it and
    release the places. Confirmed: refund single days still inside their
    refund window. Other statuses just explain where the booking is.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";
    import { toast } from "svelte-sonner";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import ReviewBooking, { type ReviewChild } from "$lib/features/bookings/components/ReviewBooking.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { BookingGroupLineResponse } from "$lib/api/schema";
    import { formatDate, formatTimestamp } from "$lib/utils/helpers";

    let { data } = $props();

    const bookingApi = createBookingApi();

    const group = $derived(data.group);

    const bookingsById = $derived(
        new Map(group.bookings.map((booking) => [booking.id, booking]))
    );

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
                bookingId: booking.id,
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

    // A confirmed booking shows when it was paid (if recorded) in place of
    // the generic message.
    const statusMessage = $derived.by(() => {
        const message = STATUS_MESSAGES[group.status];

        if (group.status === "CONFIRMED" && group.paid_at) {
            return { ...message, body: formatTimestamp(group.paid_at) };
        }

        return message;
    });

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

    // Stub: refunds will go straight to Stripe, which isn't wired yet. The
    // backend decides which days are refundable (is_refundable) and the
    // refund endpoint will check it again.
    function requestRefund(booking: BookingGroupLineResponse) {
        const day = formatDate(booking.service_date);

        if (!window.confirm(`Refund ${booking.child_name} on ${day}?`)) {
            return;
        }

        toast.info("Refunds aren't available yet.");
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

<Page>
    <PageHeader
        title={group.status === "PENDING" ? "Review your booking" : "Your booking"}
    />

    {#if group.status !== "PENDING"}
        <Card border>
            <h2 class="text-lg font-extrabold text-(--text)">
                {statusMessage?.title ?? "This booking can't be changed"}
            </h2>

            <p class="text-sm text-(--text-muted)">
                {statusMessage?.body ?? ""}
            </p>
        </Card>
    {/if}

    <ReviewBooking
        serviceName={group.bookings[0]?.service_name ?? "Booking"}
        currency={group.currency}
        children={reviewChildren}
    >
        {#snippet lineActions(line)}
            {@const booking = line.bookingId ? bookingsById.get(line.bookingId) : undefined}

            {#if booking?.payment_status === "REFUNDED"}
                <span class="text-sm text-(--text-muted)">
                    Refunded
                </span>
            {:else if booking?.is_refundable}
                <Button
                    variant="ghost"
                    onclick={() => requestRefund(booking)}
                >
                    Refund
                </Button>

                <span class="text-sm text-(--text-muted)">
                    Until {formatDate(booking.refundable_until)}
                </span>
            {:else if booking?.booking_status === "CONFIRMED"}
                <span class="text-sm text-(--text-muted)">
                    Not refundable
                </span>
            {/if}
        {/snippet}
    </ReviewBooking>

    {#if group.status === "PENDING"}
        <ActionBar sticky>
            <Button
                variant="ghost"
                onclick={cancelBooking}
                isLoading={isCancelling}
                isDisabled={isPaying}
            >
                Cancel booking
            </Button>

            <Button
                onclick={continueToPayment}
                isLoading={isPaying}
                isDisabled={isCancelling}
            >
                Continue to payment
            </Button>
        </ActionBar>
    {:else}
        <HyperTextLink href={`/${data.locationCode}/bookings`}>
            Back to bookings
        </HyperTextLink>
    {/if}
</Page>
