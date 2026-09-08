<script lang="ts">
    import SelectService from "./SelectService.svelte";
    import SelectChildDates from "./SelectChildDates.svelte";
    import ReviewBooking from "./ReviewBooking.svelte";

    import type { LocationServiceSelectionResponse } from "$lib/api/public/types/location-services";
    import type { ChildTableResponse } from "$lib/api/public/types/children";
    import type { LocationServiceDayTableResponse } from "$lib/api/public/types/location-service-days";

    let {
        locationServices,
        children,
        serviceDays,
        onConfirm,
    }: {
        locationServices: LocationServiceSelectionResponse[];
        children: ChildTableResponse[];
        serviceDays: LocationServiceDayTableResponse[];
        onConfirm: () => void;
    } = $props();

    let step = $state(1);

    let selectedService = $state<LocationServiceSelectionResponse | null>(null);
    let selectedChildIds = $state<string[]>([]);
    let selectedDatesByChild = $state<Record<string, string[]>>({});

    const selectedServiceDays = $derived.by(() => {
        if (!selectedService) {
            return [];
        }

        const locationServiceId = selectedService.id;

        return serviceDays.filter(
            (day) =>
                day.location_service_id === locationServiceId
        );
    });

    function selectService(
        locationService: LocationServiceSelectionResponse,
    ) {
        selectedService = locationService;
        selectedChildIds = [];
        selectedDatesByChild = {};
        step = 2;
    }

    function back() {
        if (step > 1) {
            step--;
        }
    }

    function next() {
        if (step < 3) {
            step++;
        }
    }
</script>

<div class="mx-auto w-full max-w-5xl">
    <div class="mb-8">
        <p class="text-sm font-medium text-gray-500">
            Step {step} of 3
        </p>

        <h1 class="mt-1 text-2xl font-semibold text-gray-900">
            {#if step === 1}
                Choose a service
            {:else if step === 2}
                Choose children and dates
            {:else}
                Review your booking
            {/if}
        </h1>

        {#if selectedService && step > 1}
            <p class="mt-2 text-sm text-gray-500">
                {selectedService.service_name}
            </p>
        {/if}
    </div>

    {#if step === 1}
        <SelectService
            {locationServices}
            onSelect={selectService}
        />

    {:else if step === 2 && selectedService}
        <SelectChildDates
            {children}
            serviceDays={selectedServiceDays}
            bind:selectedChildIds
            bind:selectedDatesByChild
            onBack={back}
            onContinue={next}
        />

    {:else if step === 3 && selectedService}
        <ReviewBooking
            {selectedService}
            {children}
            {serviceDays}
            {selectedDatesByChild}
            onBack={back}
            {onConfirm}
        />
    {/if}
</div>