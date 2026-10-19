import { createBookingApi } from "$lib/api/public/adapters/bookings";

import { BOOKING_GROUPS_PAGE_SIZE } from "$lib/features/bookings/types";
import { bookingTabs } from "$lib/navigation/tabs";

import type { PageLoad } from "./$types";

// Both tabs' first pages up front, so switching tabs doesn't wait.
export const load: PageLoad = async ({
    depends,
    fetch,
}) => {
    depends("app:booking-groups");

    const bookingApi =
        createBookingApi(fetch);

    const firstPage = {
        page: 1,
        limit: BOOKING_GROUPS_PAGE_SIZE,
    };

    const [upcomingResponse, historyResponse] = await Promise.all([
        bookingApi.listGroups({ scope: bookingTabs.UPCOMING }, firstPage),
        bookingApi.listGroups({ scope: bookingTabs.HISTORY }, firstPage),
    ]);

    return {
        bookingGroups: {
            [bookingTabs.UPCOMING]: upcomingResponse.data ?? [],
            [bookingTabs.HISTORY]: historyResponse.data ?? [],
        },
    };
};
