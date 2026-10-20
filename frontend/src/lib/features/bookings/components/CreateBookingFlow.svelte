<!--
    New booking, in three steps: service, children and dates, review. The
    route wraps it in a Page.
-->
<script lang="ts">
    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";

    import { formatTimeRange } from "$lib/utils/helpers";
    import { latePolicy, refundPolicy } from "$lib/features/services/policies";

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
                        time: formatTimeRange(service.start_time, service.end_time),
                        priceCents: service.current_price_cents,
                    })),
                };
            });
    });

    const STEP_TITLES: Record<number, string> = {
        1: "Choose a service",
        2: "Choose children and dates",
        3: "Review your booking",
    };

    let isSubmitting = $state(false);

    async function submitBooking() {
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

<PageHeader
    eyebrow={`Step ${step} of 3`}
    title={STEP_TITLES[step]}
    description={step > 1 ? selectedService?.service_name : undefined}
/>

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
    />

    <!-- What they're agreeing to before paying. -->
    <Card border>
        <ul class="flex flex-col gap-1 text-sm text-(--text-muted)">
            <li>You'll pay by card on the next screen.</li>
            <li>{refundPolicy(selectedService.refund_cutoff_days)}</li>

            {#if latePolicy(selectedService)}
                <li>{latePolicy(selectedService)}</li>
            {/if}
        </ul>
    </Card>

    <ActionBar sticky>
        <Button variant="ghost" onclick={back}>
            Back
        </Button>

        <Button onclick={submitBooking} isLoading={isSubmitting}>
            Continue to payment
        </Button>
    </ActionBar>
{/if}
