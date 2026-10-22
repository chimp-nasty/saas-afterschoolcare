import { createLocationServicesApi } from "$lib/api/public/adapters/location-services";
import { createChildrenApi } from "$lib/api/public/adapters/children";
import { createCustomerApi } from "$lib/api/public/adapters/customer";
import { createLocationBrandingApi } from "$lib/api/tenancy/adapters/location-branding";
import { createLocationServiceDaysApi } from "$lib/api/public/adapters/location-service-days";

import type { PageLoad } from "../$types";

export const load: PageLoad = async ({
    depends,
    fetch,
    params,
}) => {
    const locationServicesApi =
        createLocationServicesApi(fetch);

    const childrenApi =
        createChildrenApi(fetch);

    const locationServiceDaysApi =
        createLocationServiceDaysApi(fetch);

    const customerApi =
        createCustomerApi(fetch);

    const [
        locationServicesResponse,
        childrenResponse,
        serviceDaysResponse,
        profileResponse,
        bookingsOpenResponse,
    ] = await Promise.all([
        locationServicesApi.list(),

        childrenApi.list({
            is_active: true,
        }),

        locationServiceDaysApi.list({
            is_open: true,
        }),

        // Booking needs a complete profile, emergency contact included.
        customerApi.getProfile(),

        // And the centre taking payments (its Stripe account connected).
        createLocationBrandingApi(fetch).bookingsOpen(params.location_code),
    ]);

    depends("app:new-booking");

    return {
        locationServices:
            locationServicesResponse.data ?? [],

        children:
            childrenResponse.data ?? [],

        serviceDays:
            serviceDaysResponse.data ?? [],

        profile:
            profileResponse.data ?? null,

        bookingsOpen:
            bookingsOpenResponse.data ?? false,
    };
};