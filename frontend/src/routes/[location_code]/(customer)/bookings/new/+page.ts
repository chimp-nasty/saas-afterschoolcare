import { createLocationServicesApi } from "$lib/api/public/adapters/location-services";
import { createChildrenApi } from "$lib/api/public/adapters/children";
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

    const [
        locationServicesResponse,
        childrenResponse,
        serviceDaysResponse,
    ] = await Promise.all([
        locationServicesApi.list(),

        childrenApi.list({
            is_active: true,
        }),

        locationServiceDaysApi.list({
            is_open: true,
        }),
    ]);

    depends("app:new-booking");

    return {
        locationServices:
            locationServicesResponse.data ?? [],

        children:
            childrenResponse.data ?? [],

        serviceDays:
            serviceDaysResponse.data ?? [],
    };
};