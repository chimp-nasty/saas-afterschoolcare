<script lang="ts">
    import SelectService from "./SelectService.svelte";
    import SelectChildDates from "./SelectChildDates.svelte";
    import ReviewBooking, { type ReviewChild } from "./ReviewBooking.svelte";

    import type {
        ChildTableResponse,
        CreateBookingRequest,
        LocationServiceDayTableResponse,
        LocationServiceSelectionResponse,
    } from "$lib/api/schema";

    let {
        locationServices,
        children,
        serviceDays,
        onConfirm,
    }: {
        locationServices: LocationServiceSelectionResponse[];
        children: ChildTableResponse[];
        serviceDays: LocationServiceDayTableResponse[];
        onConfirm: (body: CreateBookingRequest) => Promise<unknown>;
    } = $props();

    let step = $state(1);

    let selectedService = $state<LocationServiceSelectionResponse | null>(null);
    let selectedChildIds = $state<string[]>([]);
    let selectedDatesByChild = $state<Record<string, string[]>>({});

    // One key per attempt: re-submitting the same selection (double click,
    // retry) resumes the same booking group instead of creating another.
    let idempotencyKey = $state(crypto.randomUUID());

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
        idempotencyKey = crypto.randomUUID();
        step = 2;
    }

    function buildRequest(): CreateBookingRequest {
        const dayIdByDate = new Map(
            selectedServiceDays.map((day) => [day.service_date, day.id])
        );

        return {
            idempotency_key: idempotencyKey,
            bookings: Object.entries(selectedDatesByChild)
                .filter(([, dates]) => dates.length > 0)
                .map(([childId, dates]) => ({
                    child_id: childId,
                    location_service_days: dates
                        .map((date) => dayIdByDate.get(date))
                        .filter((id): id is string => id !== undefined),
                })),
        };
    }

    const reviewChildren = $derived.by((): ReviewChild[] => {
        if (!selectedService) {
            return [];
        }

        const service = selectedService;

        return Object.entries(selectedDatesByChild)
            .filter(([, dates]) => dates.length > 0)
            .map(([childId, dates]) => {
                const child = children.find((c) => c.id === childId);

                return {
                    childId,
                    childName: child
                        ? `${child.first_name} ${child.last_name}`
                        : "Child",
                    lines: dates.map((date) => ({
                        date,
                        serviceName: service.service_name,
                        priceCents: service.current_price_cents,
                    })),
                };
            });
    });

    let isSubmitting = $state(false);

    async function confirm() {
        isSubmitting = true;

        try {
            await onConfirm(buildRequest());
        } finally {
            isSubmitting = false;
        }
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
            serviceName={selectedService.service_name}
            currency={selectedService.currency}
            children={reviewChildren}
        >
            {#snippet actions()}
                <button
                    type="button"
                    onclick={back}
                    class="rounded-lg border border-gray-300 px-5 py-2.5 font-medium text-gray-700 hover:bg-gray-50"
                >
                    Back
                </button>

                <button
                    type="button"
                    onclick={confirm}
                    disabled={isSubmitting}
                    class="rounded-lg bg-gray-900 px-5 py-2.5 font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
                >
                    {isSubmitting ? "Booking…" : "Continue to payment"}
                </button>
            {/snippet}
        </ReviewBooking>
    {/if}
</div>