<!--
    Review a booking group. Pending: continue to Stripe, or cancel it and
    release the places. Confirmed: refund single days still inside their
    refund window (the webhook finishes each refund, so it shows as
    processing for a few seconds). Other statuses explain where it is.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import ReviewBooking, { type ReviewChild } from "$lib/features/bookings/components/ReviewBooking.svelte";
    import CentreCard from "$lib/features/location/components/CentreCard.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import { createRefundsApi } from "$lib/api/public/adapters/refunds";
    import type { BookingGroupLineResponse } from "$lib/api/schema";
    import { formatDate, formatMoney, formatTimeRange, formatTimestamp } from "$lib/utils/helpers";

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
                time: formatTimeRange(booking.start_time, booking.end_time),
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

    const REFUNDED_MESSAGE = {
        title: "This booking was refunded",
        body: "The money has gone back to your card, and the places were released.",
    };

    const refundedCents = $derived(
        group.bookings
            .filter((booking) => booking.payment_status === "REFUNDED")
            .reduce((total, booking) => total + booking.price_snapshot_cents, 0)
    );

    // Every session refunded reads as "refunded", not "cancelled".
    const isFullyRefunded = $derived(
        group.bookings.length > 0 &&
        group.bookings.every((booking) => booking.payment_status === "REFUNDED")
    );

    // A confirmed booking shows when it was paid (if recorded) in place of
    // the generic message.
    const statusMessage = $derived.by(() => {
        if (isFullyRefunded) {
            return REFUNDED_MESSAGE;
        }

        const message = STATUS_MESSAGES[group.status];

        if (group.status === "CONFIRMED" && group.paid_at) {
            return { ...message, body: formatTimestamp(group.paid_at) };
        }

        return message;
    });

    let isPaying = $state(false);

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

    // --- Refunds -----------------------------------------------------------

    const refundsApi = createRefundsApi();

    // The webhook usually confirms within seconds; check back a few times
    // so "Refund processing" turns into "Refunded" without a reload.
    async function refreshWhileProcessing() {
        for (let attempt = 0; attempt < 5; attempt++) {
            await new Promise((resolve) => setTimeout(resolve, 2000));
            await invalidate("app:booking-group");

            if (!group.bookings.some((booking) => booking.refund_status === "PENDING")) {
                return;
            }
        }
    }

    async function refund(booking: BookingGroupLineResponse) {
        const day = formatDate(booking.service_date);
        const amount = formatMoney(booking.price_snapshot_cents, booking.currency);

        await confirmAction({
            title: "Refund this session?",
            message: `${booking.child_name} on ${day}: ${amount} goes back to your card, and the place is released.`,
            confirmLabel: "Refund",
            tone: "danger",
            action: async () => {
                const response = await refundsApi.create(booking.id);

                await invalidate("app:booking-group");

                if (response.ok) {
                    void refreshWhileProcessing();
                }
            },
        });
    }

    async function cancelBooking() {
        await confirmAction({
            title: "Cancel this booking?",
            message: "The places will be released, and you can make a new booking at any time.",
            confirmLabel: "Cancel booking",
            tone: "danger",
            action: async () => {
                const response = await bookingApi.cancelGroup(group.booking_group_id);

                if (response.ok) {
                    await invalidate("app:home-bookings");
                    await goto(`/${data.locationCode}/home`);
                    return;
                }

                await invalidate("app:booking-group");
            },
        });
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

            {#if group.receipt_url}
                <HyperTextLink href={group.receipt_url} external>
                    View receipt
                </HyperTextLink>
            {/if}
        </Card>
    {/if}

    <ReviewBooking
        serviceName={group.bookings[0]?.service_name ?? "Booking"}
        currency={group.currency}
        children={reviewChildren}
        {refundedCents}
    >
        {#snippet lineActions(line)}
            {@const booking = line.bookingId ? bookingsById.get(line.bookingId) : undefined}

            {#if booking?.payment_status === "REFUNDED"}
                <span class="text-sm text-(--text-muted)">
                    Refunded
                </span>
            {:else if booking?.refund_status === "PENDING"}
                <span class="text-sm text-(--text-muted)">
                    Refund processing
                </span>
            {:else if booking?.is_refundable}
                <Button
                    variant="ghost"
                    onclick={() => refund(booking)}
                >
                    Refund
                </Button>

                <span class="text-sm text-(--text-muted)">
                    {booking.refund_status === "FAILED"
                        ? "Last refund didn't go through"
                        : `Until ${formatDate(booking.refundable_until)}`}
                </span>
            {:else if booking?.booking_status === "CONFIRMED"}
                <span class="text-sm text-(--text-muted)">
                    Not refundable
                </span>
            {/if}
        {/snippet}
    </ReviewBooking>

    <CentreCard
        location={data.location}
        note="Sign your child in when you drop them off and out when you collect them."
    />

    {#if group.status === "PENDING"}
        <ActionBar sticky>
            <Button
                variant="ghost"
                onclick={cancelBooking}
                isDisabled={isPaying}
            >
                Cancel booking
            </Button>

            <Button
                onclick={continueToPayment}
                isLoading={isPaying}
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
