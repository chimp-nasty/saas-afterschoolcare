<script lang="ts">
    import { goto } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import BookingGroupList from "$lib/features/bookings/components/BookingGroupList.svelte";

    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import type { BookingGroupSummaryResponse } from "$lib/api/schema";

    import { BOOKING_GROUPS_PAGE_SIZE } from "$lib/features/bookings/types";
    import { bookingTabs, type BookingTab } from "$lib/navigation/tabs";

    let { data } = $props();

    const bookingApi = createBookingApi();

    let activeTab = $state<string>(bookingTabs.UPCOMING);

    const tabs = [
        { id: bookingTabs.UPCOMING, label: "Upcoming" },
        { id: bookingTabs.HISTORY, label: "History" },
    ];

    const EMPTY_MESSAGES: Record<BookingTab, string> = {
        [bookingTabs.UPCOMING]: "You have no upcoming bookings.",
        [bookingTabs.HISTORY]: "Past and cancelled bookings will show here.",
    };

    // Each tab starts from the loader's first page; "Load more" appends the
    // next. Kept per tab so switching back doesn't lose loaded pages.
    type TabPages = {
        extraGroups: BookingGroupSummaryResponse[];
        page: number;
        lastPageSize: number | null;
        isLoading: boolean;
    };

    function emptyPages(): TabPages {
        return { extraGroups: [], page: 1, lastPageSize: null, isLoading: false };
    }

    let pages = $state<Record<BookingTab, TabPages>>({
        [bookingTabs.UPCOMING]: emptyPages(),
        [bookingTabs.HISTORY]: emptyPages(),
    });

    function bookingGroups(tab: BookingTab): BookingGroupSummaryResponse[] {
        return [...data.bookingGroups[tab], ...pages[tab].extraGroups];
    }

    function hasMore(tab: BookingTab): boolean {
        return (
            (pages[tab].lastPageSize ?? data.bookingGroups[tab].length)
            === BOOKING_GROUPS_PAGE_SIZE
        );
    }

    async function loadMore(tab: BookingTab) {
        const tabPages = pages[tab];

        tabPages.isLoading = true;

        try {
            const response = await bookingApi.listGroups(
                { scope: tab },
                { page: tabPages.page + 1, limit: BOOKING_GROUPS_PAGE_SIZE },
            );

            if (!response.ok || !response.data) {
                return;
            }

            tabPages.extraGroups = [...tabPages.extraGroups, ...response.data];
            tabPages.lastPageSize = response.data.length;
            tabPages.page += 1;
        } finally {
            tabPages.isLoading = false;
        }
    }
</script>

<Page>
    <PageHeader title="Bookings">
        {#snippet actions()}
            <Button onclick={() => goto(`/${data.locationCode}/bookings/new`)}>
                Book now
            </Button>
        {/snippet}
    </PageHeader>

    <TabbedPanels
        {tabs}
        bind:activeTab
        queryParam="tab"
    >
        {#snippet panel(id)}
            {@const tab = id as BookingTab}

            <BookingGroupList
                bookingGroups={bookingGroups(tab)}
                locationCode={data.locationCode}
                hasMore={hasMore(tab)}
                isLoading={pages[tab].isLoading}
                emptyMessage={EMPTY_MESSAGES[tab]}
                onLoadMore={() => loadMore(tab)}
            />
        {/snippet}
    </TabbedPanels>
</Page>
