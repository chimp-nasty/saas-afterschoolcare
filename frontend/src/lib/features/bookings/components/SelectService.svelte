<script lang="ts">
    import type { LocationServiceSelectionResponse } from "$lib/api/schema";
    import { ChevronRight } from "lucide-svelte";

    import { formatMoney } from "$lib/utils/helpers";

    let {
        locationServices,
        onSelect,
    }: {
        locationServices: LocationServiceSelectionResponse[];
        onSelect: (
            locationService: LocationServiceSelectionResponse
        ) => void;
    } = $props();

</script>

<!-- One tile per service; tapping one moves to the next step. -->
<div class="flex flex-col gap-4">
    {#each locationServices as locationService (locationService.id)}
        <button
            type="button"
            onclick={() => onSelect(locationService)}
            class="
                flex min-h-24 w-full items-center justify-between gap-4
                rounded-2xl border border-(--border) bg-(--surface) p-5
                text-left shadow-sm transition
                hover:border-(--primary)
                focus-visible:border-(--primary) focus-visible:outline-none
            "
        >
            <div class="flex flex-col gap-2">
                <h2 class="text-lg font-extrabold text-(--text)">
                    {locationService.service_name}
                </h2>

                <p>
                    <span class="text-base font-semibold text-(--text)">
                        {formatMoney(
                            locationService.current_price_cents,
                            locationService.currency,
                        )}
                    </span>

                    <span class="text-sm text-(--text-muted)">
                        / session
                    </span>
                </p>
            </div>

            <ChevronRight size={20} class="shrink-0 text-(--text-muted)" />
        </button>
    {/each}
</div>
