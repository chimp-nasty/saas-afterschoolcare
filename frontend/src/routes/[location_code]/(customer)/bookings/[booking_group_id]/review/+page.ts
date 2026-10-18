import { error } from "@sveltejs/kit";

import { createBookingApi } from "$lib/api/public/adapters/bookings";

import type { PageLoad } from "./$types";

export const load: PageLoad = async ({
    depends,
    fetch,
    params,
}) => {
    depends("app:booking-group");

    const bookingApi =
        createBookingApi(fetch);

    const groupResponse =
        await bookingApi.getGroup(params.booking_group_id);

    if (!groupResponse.ok || !groupResponse.data) {
        error(404, "Booking not found");
    }

    return {
        group: groupResponse.data,
    };
};
