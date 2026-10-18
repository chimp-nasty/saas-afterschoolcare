<!--
    "My bookings": one card per checkout, linking to its review screen.
    The page owns loading; this just renders and asks for more.
-->
<script lang="ts">
    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";

    import type { BookingGroupSummaryResponse } from "$lib/api/schema";
    import { formatDateDDMMYYYY } from "$lib/utils/helpers";

    let {
        bookingGroups,
        locationCode,
        hasMore,
        isLoading = false,
        onLoadMore,
        onBookNow,
    }: {
        bookingGroups: BookingGroupSummaryResponse[];
        locationCode: string;
        hasMore: boolean;
        isLoading?: boolean;
        onLoadMore: () => void;
        onBookNow: () => void;
    } = $props();

    const STATUS_LABELS: Record<string, string> = {
        PENDING: "Awaiting payment",
        CONFIRMED: "Confirmed",
        EXPIRED: "Expired",
        CANCELLED: "Cancelled",
    };

    function formatDates(group: BookingGroupSummaryResponse): string {
        const first = formatDateDDMMYYYY(group.first_date);

        return group.first_date === group.last_date
            ? first
            : `${first} – ${formatDateDDMMYYYY(group.last_date)}`;
    }

    function formatPrice(group: BookingGroupSummaryResponse): string {
        return new Intl.NumberFormat("en-AU", {
            style: "currency",
            currency: group.currency,
        }).format(group.total_cents / 100);
    }
</script>

<Card>
    <div class="flex flex-col gap-4">
        {#each bookingGroups as group (group.booking_group_id)}
            <DataCard
                title={group.service_name}
                href={`/${locationCode}/bookings/${group.booking_group_id}/review`}
                data={[
                    { label: "Status", value: STATUS_LABELS[group.status] ?? group.status },
                    { label: "Children", value: group.child_names.join(", ") },
                    { label: "Dates", value: formatDates(group) },
                    { label: "Sessions", value: group.booking_count },
                    { label: "Total", value: formatPrice(group) },
                ]}
            />
        {:else}
            <p class="px-1 py-4 text-sm text-(--text-muted)">
                You haven't made any bookings yet.
            </p>
        {/each}

        {#if hasMore}
            <Button
                variant="ghost"
                fullWidth
                {isLoading}
                onclick={onLoadMore}
            >
                Load more
            </Button>
        {/if}

        <Button
            fullWidth
            onclick={onBookNow}
        >
            Book Now
        </Button>
    </div>
</Card>
