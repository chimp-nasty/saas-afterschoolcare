import { createBookingApi } from "$lib/api/public/adapters/bookings";

import { BOOKING_GROUPS_PAGE_SIZE } from "$lib/features/bookings/types";

import type { PageLoad } from "./$types";

export const load: PageLoad = async ({
    depends,
    fetch,
}) => {
    depends("app:booking-groups");

    const bookingApi =
        createBookingApi(fetch);

    const groupsResponse = await bookingApi.listGroups({
        page: 1,
        limit: BOOKING_GROUPS_PAGE_SIZE,
    });

    return {
        bookingGroups:
            groupsResponse.data ?? [],
    };
};
