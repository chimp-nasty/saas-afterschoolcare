import { createLocationServicesApi } from "$lib/api/public/adapters/location-services";
import { createChildrenApi } from "$lib/api/public/adapters/children";
import { createCustomerApi } from "$lib/api/public/adapters/customer";
import { createLocationServiceDaysApi } from "$lib/api/public/adapters/location-service-days";

import type { PageLoad } from "../$types";

export const load: PageLoad = async ({
    depends,
    fetch,
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
    };
};