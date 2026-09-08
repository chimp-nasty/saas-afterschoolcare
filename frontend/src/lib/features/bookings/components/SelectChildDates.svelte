<script lang="ts">
    import ServiceDayCalendar from "./ServiceDayCalendar.svelte";

    import type { ChildTableResponse } from "$lib/api/public/types/children";
    import type { LocationServiceDayTableResponse } from "$lib/api/public/types/location-service-days";

    let {
        children,
        serviceDays,
        selectedChildIds = $bindable(),
        selectedDatesByChild = $bindable(),
        onBack,
        onContinue,
    }: {
        children: ChildTableResponse[];
        serviceDays: LocationServiceDayTableResponse[];
        selectedChildIds: string[];
        selectedDatesByChild: Record<string, string[]>;
        onBack: () => void;
        onContinue: () => void;
    } = $props();

    let selectedDates = $state<string[]>([]);

    function toggleChild(
        childId: string
    ) {
        if (selectedChildIds.includes(childId)) {
            selectedChildIds =
                selectedChildIds.filter(
                    (id) => id !== childId
                );
        } else {
            selectedChildIds = [
                ...selectedChildIds,
                childId,
            ];
        }

        syncSelectedDates();
    }

    function syncSelectedDates() {
        if (selectedChildIds.length === 0) {
            selectedDates = [];
            return;
        }

        const [firstChildId] =
            selectedChildIds;

        selectedDates =
            selectedDatesByChild[firstChildId] ?? [];
    }

    $effect(() => {
        if (selectedChildIds.length === 0) {
            return;
        }

        const next = {
            ...selectedDatesByChild,
        };

        for (const childId of selectedChildIds) {
            next[childId] = [
                ...selectedDates,
            ];
        }

        selectedDatesByChild = next;
    });

    const canContinue = $derived(
        Object.values(selectedDatesByChild)
            .some((dates) => dates.length > 0)
    );
</script>

<div class="space-y-8">
    <section>
        <h2 class="text-lg font-semibold text-gray-900">
            Who are you booking for?
        </h2>

        <p class="mt-1 text-sm text-gray-500">
            Select one or more children.
        </p>

        <div class="mt-4 flex flex-wrap gap-3">
            {#each children as child}
                <button
                    type="button"
                    onclick={() =>
                        toggleChild(child.id)
                    }
                    class={[
                        "rounded-lg border px-4 py-3 text-left transition",
                        selectedChildIds.includes(child.id)
                            ? "border-gray-900 bg-gray-900 text-white"
                            : "border-gray-200 bg-white text-gray-900 hover:border-gray-300",
                    ]}
                >
                    <span class="font-medium">
                        {child.first_name}
                        {child.last_name}
                    </span>
                </button>
            {/each}
        </div>
    </section>

    <section>
        <h2 class="text-lg font-semibold text-gray-900">
            Choose dates
        </h2>

        {#if selectedChildIds.length === 0}
            <p class="mt-1 text-sm text-gray-500">
                Select a child before choosing dates.
            </p>
        {:else}
            <p class="mt-1 text-sm text-gray-500">
                Dates will be applied to all currently selected children.
            </p>
        {/if}

        <div class="mt-4">
            {#if selectedChildIds.length > 0}
                <ServiceDayCalendar
                    {serviceDays}
                    bind:selectedDates
                />
            {/if}
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
            onclick={onContinue}
            disabled={!canContinue}
            class="rounded-lg bg-gray-900 px-5 py-2.5 font-medium text-white hover:bg-gray-800 disabled:cursor-not-allowed disabled:opacity-40"
        >
            Continue
        </button>
    </div>
</div>