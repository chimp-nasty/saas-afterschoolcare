<!--
    One "My bookings" tab: a card per checkout, linking to its review screen.
    The page owns loading; this just renders and asks for more.
-->
<script lang="ts">
    import Button from "$lib/components/actions/Button.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";
    import EmptyState from "$lib/components/text/EmptyState.svelte";

    import type { BookingGroupSummaryResponse } from "$lib/api/schema";
    import { BOOKING_STATUS_LABELS } from "$lib/features/bookings/status";
    import { formatDateRange, formatMoney, formatTimestamp } from "$lib/utils/helpers";

    let {
        bookingGroups,
        locationCode,
        hasMore,
        isLoading = false,
        emptyMessage,
        onLoadMore,
    }: {
        bookingGroups: BookingGroupSummaryResponse[];
        locationCode: string;
        hasMore: boolean;
        isLoading?: boolean;
        emptyMessage: string;
        onLoadMore: () => void;
    } = $props();

    // "Confirmed Tue, 20 Oct" once paid; just the label otherwise.
    function formatStatus(group: BookingGroupSummaryResponse): string {
        const label = BOOKING_STATUS_LABELS[group.status];

        return group.status === "CONFIRMED" && group.paid_at
            ? `${label} ${formatTimestamp(group.paid_at)}`
            : label;
    }

</script>

<div class="flex flex-col gap-4">
    {#each bookingGroups as group (group.booking_group_id)}
        <DataCard
            title={group.service_name}
            href={`/${locationCode}/bookings/${group.booking_group_id}/review`}
            data={[
                { label: "Reference", value: group.reference },
                { label: "Status", value: formatStatus(group) },
                { label: "Children", value: group.child_names.join(", ") },
                { label: "Dates", value: formatDateRange(group.first_date, group.last_date) },
                { label: "Sessions", value: group.booking_count },
                { label: "Total", value: formatMoney(group.total_cents, group.currency) },
            ]}
        />
    {:else}
        <EmptyState message={emptyMessage} />
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
</div>
