<script lang="ts">
    import { untrack } from "svelte";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";

    import ServiceDayCalendar from "./ServiceDayCalendar.svelte";

    import type {
        ChildTableResponse,
        LocationServiceDayTableResponse,
    } from "$lib/api/schema";

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

    // One set of dates for every selected child. Starts from what was picked
    // before (e.g. coming back from review).
    let selectedDates = $state<string[]>(
        untrack(() => selectedDatesByChild[selectedChildIds[0]] ?? [])
    );

    function toggleChild(
        childId: string
    ) {
        selectedChildIds = selectedChildIds.includes(childId)
            ? selectedChildIds.filter((id) => id !== childId)
            : [...selectedChildIds, childId];
    }

    const canContinue = $derived(
        selectedChildIds.length > 0 &&
        selectedDates.length > 0
    );

    function continueToReview() {
        selectedDatesByChild = Object.fromEntries(
            selectedChildIds.map((childId) => [childId, [...selectedDates]])
        );

        onContinue();
    }
</script>

<section class="flex flex-col gap-4">
    <div>
        <h2 class="text-lg font-extrabold text-(--text)">
            Who are you booking for?
        </h2>

        <p class="text-sm text-(--text-muted)">
            Select one or more children.
        </p>
    </div>

    <div class="flex flex-wrap gap-3">
        {#each children as child (child.id)}
            {@const isSelected = selectedChildIds.includes(child.id)}

            <button
                type="button"
                aria-pressed={isSelected}
                onclick={() => toggleChild(child.id)}
                class={[
                    "min-h-11 rounded-lg border px-4 text-left font-semibold transition",
                    isSelected
                        ? "border-(--primary) bg-(--primary) text-white"
                        : "border-(--border) bg-(--surface) text-(--text) hover:border-(--primary)",
                ]}
            >
                {child.first_name}
                {child.last_name}
            </button>
        {/each}
    </div>
</section>

<section class="flex flex-col gap-4">
    <div>
        <h2 class="text-lg font-extrabold text-(--text)">
            Choose dates
        </h2>

        <p class="text-sm text-(--text-muted)">
            {selectedChildIds.length === 0
                ? "Select a child before choosing dates."
                : "Dates apply to every selected child."}
        </p>
    </div>

    {#if selectedChildIds.length > 0}
        <ServiceDayCalendar
            {serviceDays}
            {selectedChildIds}
            childNames={Object.fromEntries(
                children.map((child) => [child.id, child.first_name])
            )}
            bind:selectedDates
        />
    {/if}
</section>

<ActionBar sticky>
    <Button variant="ghost" onclick={onBack}>
        Back
    </Button>

    <Button onclick={continueToReview} isDisabled={!canContinue}>
        Continue
    </Button>
</ActionBar>
