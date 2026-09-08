<script lang="ts">
    import type { LocationServiceSelectionResponse } from "$lib/api/public/types/location-services";

    let {
        locationServices,
        onSelect,
    }: {
        locationServices: LocationServiceSelectionResponse[];
        onSelect: (
            locationService: LocationServiceSelectionResponse
        ) => void;
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
</script>

<div class="grid w-full max-w-4xl grid-cols-1 gap-4 md:grid-cols-2">
    {#each locationServices as locationService}
        <button
            type="button"
            onclick={() => onSelect(locationService)}
            class="
                flex min-h-32 items-center justify-between
                rounded-xl border border-gray-200 bg-white p-6
                text-left shadow-sm
                transition
                hover:-translate-y-0.5 hover:border-gray-300 hover:shadow-md
                focus:outline-none focus:ring-2 focus:ring-gray-300
            "
        >
            <div class="flex flex-col gap-4">
                <h3 class="text-lg font-semibold text-gray-900">
                    {locationService.service_name}
                </h3>

                <div>
                    <span class="text-2xl font-semibold text-gray-900">
                        {formatPrice(
                            locationService.current_price_cents,
                            locationService.currency,
                        )}
                    </span>

                    <span class="ml-1 text-sm text-gray-500">
                        / session
                    </span>
                </div>
            </div>

            <span class="text-xl text-gray-400">
                →
            </span>
        </button>
    {/each}
</div>