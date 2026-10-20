import { createBookingApi } from "$lib/api/public/adapters/bookings";
import { createMedicalReviewsApi } from "$lib/api/public/adapters/medicalReviews";

import type { PageLoad } from "./$types";

// The customer home's week strip can step back and forward; load enough
// either side of today to cover that.
const WEEKS_BACK = 4;
const WEEKS_AHEAD = 12;

function toDateKey(date: Date): string {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, "0");
    const day = String(date.getDate()).padStart(2, "0");

    return `${year}-${month}-${day}`;
}

function daysFromToday(days: number): string {
    const date = new Date();
    date.setDate(date.getDate() + days);

    return toDateKey(date);
}

export const load: PageLoad = async ({
    depends,
    fetch,
    parent,
}) => {
    depends("app:home-bookings");

    const { session } = await parent();
    const roles = session?.roles ?? [];

    // Staff, admins and superadmins get the staff home: what needs
    // attention at the location.
    if (["staff", "admin", "superadmin"].some((role) => roles.includes(role))) {
        const reviewsResponse = await createMedicalReviewsApi(fetch).list();
        const reviews = reviewsResponse.data ?? [];

        return {
            bookings: [],
            reviewsWaiting: reviews.filter((review) => review.review_status === "pending").length,
            reviewsRequested: reviews.filter((review) => review.review_status === "documentation_requested").length,
        };
    }

    // Only the customer home shows bookings.
    if (!roles.includes("customer")) {
        return {
            bookings: [],
        };
    }

    const bookingApi =
        createBookingApi(fetch);

    const bookingsResponse = await bookingApi.list(
        {
            booking_status: ["CONFIRMED", "PENDING"],
            date_from: daysFromToday(-WEEKS_BACK * 7),
            date_to: daysFromToday(WEEKS_AHEAD * 7),
        },
        {
            limit: 100,
        },
    );

    return {
        bookings:
            bookingsResponse.data ?? [],
    };
};
