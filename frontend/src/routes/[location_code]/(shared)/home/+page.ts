import { redirect } from "@sveltejs/kit";

import { createBookingApi } from "$lib/api/public/adapters/bookings";
import { createMedicalReviewsApi } from "$lib/api/public/adapters/medicalReviews";
import { createAttendanceApi } from "$lib/api/public/adapters/attendance";
import { createCustomerApi } from "$lib/api/public/adapters/customer";
import { createChildrenApi } from "$lib/api/public/adapters/children";
import { setupProgress } from "$lib/features/customer/setup";

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
    params,
    parent,
}) => {
    depends("app:home-bookings");

    const { session } = await parent();
    const roles = session?.roles ?? [];

    // Admins and superadmins get the admin home: what needs attention at
    // the location.
    if (["admin", "superadmin"].some((role) => roles.includes(role))) {
        const [reviewsResponse, rollResponse] = await Promise.all([
            createMedicalReviewsApi(fetch).list(),
            createAttendanceApi(fetch).roll(),
        ]);
        const reviews = reviewsResponse.data ?? [];

        return {
            bookings: [],
            reviewsWaiting: reviews.filter((review) => review.review_status === "pending").length,
            reviewsRequested: reviews.filter((review) => review.review_status === "documentation_requested").length,
            // Still signed in after their session ended today.
            latePickups: (rollResponse.data?.entries ?? []).filter((entry) => entry.is_late).length,
        };
    }

    // Staff have no location data on the website (docs/portals.md): their
    // home is their own account.
    if (roles.includes("staff")) {
        redirect(307, `/${params.location_code}/staff/account`);
    }

    // Only the customer home shows bookings.
    if (!roles.includes("customer")) {
        return {
            bookings: [],
        };
    }

    depends("app:customer-account");

    const bookingApi =
        createBookingApi(fetch);

    const [bookingsResponse, profileResponse, childrenResponse] = await Promise.all([
        bookingApi.list(
            {
                booking_status: ["CONFIRMED", "PENDING"],
                date_from: daysFromToday(-WEEKS_BACK * 7),
                date_to: daysFromToday(WEEKS_AHEAD * 7),
            },
            {
                limit: 100,
            },
        ),
        createCustomerApi(fetch).getProfile(),
        createChildrenApi(fetch).list({ is_active: true }),
    ]);

    return {
        bookings:
            bookingsResponse.data ?? [],
        // How far the family's setup has got (the "Finish setting up" card).
        setup: profileResponse.data
            ? setupProgress(profileResponse.data, (childrenResponse.data ?? []).length)
            : null,
    };
};
