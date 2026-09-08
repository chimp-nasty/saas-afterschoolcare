<script lang="ts">
    import type { LocationServiceSelectionResponse } from "$lib/api/public/types/location-services";
    import type { ChildTableResponse } from "$lib/api/public/types/children";
    import type { LocationServiceDayTableResponse } from "$lib/api/public/types/location-service-days";

    let {
        selectedService,
        children,
        serviceDays,
        selectedDatesByChild,
        onBack,
        onConfirm,
    }: {
        selectedService: LocationServiceSelectionResponse;
        children: ChildTableResponse[];
        serviceDays: LocationServiceDayTableResponse[];
        selectedDatesByChild: Record<string, string[]>;
        onBack: () => void;
        onConfirm: () => void;
    } = $props();

    function formatPrice(
        priceCents: number,
        currency: string,
    ): string {
        return new Intl.NumberFormat("en-AU", {
            style: "currency",
            currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(priceCents / 100);
    }

    function formatDate(date: string): string {
        return new Intl.DateTimeFormat("en-AU", {
            weekday: "short",
            day: "numeric",
            month: "short",
        }).format(new Date(`${date}T00:00:00`));
    }

    function getChild(childId: string) {
        return children.find(
            (child) => child.id === childId
        );
    }

    function getServiceDay(serviceDate: string) {
        return serviceDays.find(
            (day) =>
                day.location_service_id === selectedService.id &&
                day.service_date === serviceDate
        );
    }

    const selectedChildren = $derived(
        Object.entries(selectedDatesByChild)
            .filter(([, dates]) => dates.length > 0)
    );

    const bookingCount = $derived(
        selectedChildren.reduce(
            (total, [, dates]) => total + dates.length,
            0
        )
    );

    const totalPriceCents = $derived(
        bookingCount * selectedService.current_price_cents
    );
</script>

<div class="space-y-8">
    <section class="rounded-xl border border-gray-200 bg-white p-6">
        <div class="flex items-start justify-between gap-4">
            <div>
                <h2 class="text-lg font-semibold text-gray-900">
                    {selectedService.service_name}
                </h2>

                <p class="mt-1 text-sm text-gray-500">
                    {formatPrice(
                        selectedService.current_price_cents,
                        selectedService.currency,
                    )}
                    / session
                </p>
            </div>
        </div>
    </section>

    <div class="space-y-6">
        {#each selectedChildren as [childId, dates]}
            {@const child = getChild(childId)}

            {#if child}
                <section class="rounded-xl border border-gray-200 bg-white">
                    <div class="border-b border-gray-200 px-6 py-4">
                        <h3 class="font-semibold text-gray-900">
                            {child.first_name} {child.last_name}
                        </h3>
                    </div>

                    <div class="divide-y divide-gray-100">
                        {#each dates as date}
                            {@const serviceDay = getServiceDay(date)}

                            <div class="flex items-center justify-between px-6 py-4">
                                <div>
                                    <p class="font-medium text-gray-900">
                                        {formatDate(date)}
                                    </p>

                                    {#if serviceDay}
                                        <p class="mt-1 text-sm text-gray-500">
                                            {serviceDay.service_name}
                                        </p>
                                    {/if}
                                </div>

                                <p class="font-medium text-gray-900">
                                    {formatPrice(
                                        selectedService.current_price_cents,
                                        selectedService.currency,
                                    )}
                                </p>
                            </div>
                        {/each}
                    </div>

                    <div class="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-6 py-4">
                        <span class="text-sm font-medium text-gray-600">
                            Subtotal
                        </span>

                        <span class="font-semibold text-gray-900">
                            {formatPrice(
                                dates.length * selectedService.current_price_cents,
                                selectedService.currency,
                            )}
                        </span>
                    </div>
                </section>
            {/if}
        {/each}
    </div>

    <section class="rounded-xl border border-gray-200 bg-white p-6">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-500">
                    {bookingCount}
                    {bookingCount === 1 ? " booking" : " bookings"}
                </p>

                <p class="mt-1 text-lg font-semibold text-gray-900">
                    Total
                </p>
            </div>

            <p class="text-2xl font-semibold text-gray-900">
                {formatPrice(
                    totalPriceCents,
                    selectedService.currency,
                )}
            </p>
        </div>
    </section>

    <div class="flex items-center justify-between border-t border-gray-200 pt-6">
        <button
            type="button"
            onclick={onBack}
            class="rounded-lg border border-gray-300 px-5 py-2.5 font-medium text-gray-700 hover:bg-gray-50"
        >
            Back
        </button>

        <button
            type="button"
            onclick={onConfirm}
            class="rounded-lg bg-gray-900 px-5 py-2.5 font-medium text-white hover:bg-gray-800"
        >
            Continue to payment
        </button>
    </div>
</div>