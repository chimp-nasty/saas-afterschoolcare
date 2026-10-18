<script lang="ts">
    import { goto } from "$app/navigation";

    import BookingGroupList from "$lib/features/bookings/components/BookingGroupList.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { BookingGroupSummaryResponse } from "$lib/api/schema";

    import { BOOKING_GROUPS_PAGE_SIZE } from "$lib/features/bookings/types";

    let { data } = $props();

    const bookingApi = createBookingApi();

    // Starts from the loader's first page; "Load more" appends the next.
    let extraGroups = $state<BookingGroupSummaryResponse[]>([]);
    let page = $state(1);
    let lastPageSize = $state<number | null>(null);
    let isLoading = $state(false);

    const bookingGroups = $derived([...data.bookingGroups, ...extraGroups]);

    const hasMore = $derived(
        (lastPageSize ?? data.bookingGroups.length) === BOOKING_GROUPS_PAGE_SIZE
    );

    async function loadMore() {
        isLoading = true;

        try {
            const response = await bookingApi.listGroups({
                page: page + 1,
                limit: BOOKING_GROUPS_PAGE_SIZE,
            });

            if (!response.ok || !response.data) {
                return;
            }

            extraGroups = [...extraGroups, ...response.data];
            lastPageSize = response.data.length;
            page += 1;
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
    <BookingGroupList
        {bookingGroups}
        locationCode={data.locationCode}
        {hasMore}
        {isLoading}
        onLoadMore={loadMore}
        onBookNow={() => goto(`/${data.locationCode}/bookings/new`)}
    />
</div>
