<script lang="ts">
    import { untrack } from "svelte";
    import { Calendar } from "bits-ui";
    import { parseDate, type DateValue } from "@internationalized/date";

    import type { LocationServiceDayTableResponse } from "$lib/api/schema";
    import { ServiceDayStatus } from "../types";

    let {
        serviceDays,
        selectedDates = $bindable([]),
    }: {
        serviceDays: LocationServiceDayTableResponse[];
        selectedDates: string[];
    } = $props();

    // Starts from the parent's dates (e.g. coming back from review). After
    // that only the user's clicks change it, through onValueChange.
    let selected = $state<DateValue[]>(
        untrack(() => selectedDates.map((date) => parseDate(date)))
    );

    const dayMap = $derived.by(() => {
        const map = new Map<
            string,
            LocationServiceDayTableResponse
        >();

        for (const serviceDay of serviceDays) {
            map.set(
                serviceDay.service_date,
                serviceDay
            );
        }

        return map;
    });

    function getStatus(
        date: DateValue,
    ): ServiceDayStatus {
        const serviceDay =
            dayMap.get(date.toString());

        if (!serviceDay) {
            return ServiceDayStatus.UNAVAILABLE;
        }

        if (!serviceDay.is_open) {
            return ServiceDayStatus.CLOSED;
        }

        return ServiceDayStatus.AVAILABLE;
    }

    function isSelectable(
        date: DateValue,
    ): boolean {
        return getStatus(date) ===
            ServiceDayStatus.AVAILABLE;
    }

    const STATUS_STYLES: Record<ServiceDayStatus, string> = {
        [ServiceDayStatus.AVAILABLE]:
            "border border-(--success)/20 bg-(--success-soft) text-(--success-text) hover:bg-(--secondary)",

        [ServiceDayStatus.BOOKED]:
            "border border-(--primary)/20 bg-(--primary-soft) text-(--primary) opacity-70 cursor-not-allowed",

        [ServiceDayStatus.FULL]:
            "border border-(--danger)/20 bg-(--danger-soft) text-(--danger-text) opacity-70 cursor-not-allowed",

        [ServiceDayStatus.CLOSED]:
            "border border-(--border) bg-(--surface) text-(--text-muted) opacity-70 cursor-not-allowed",

        [ServiceDayStatus.UNAVAILABLE]:
            "border border-transparent bg-transparent text-(--text-muted) opacity-30 cursor-not-allowed",
    };
</script>

<div class="max-w-120 rounded-3xl border border-(--border) bg-(--surface-muted) p-5 shadow-sm">
    <Calendar.Root
        type="multiple"
        bind:value={selected}
        onValueChange={(value) => {
            selectedDates = value.map((date) => date.toString());
        }}
        weekdayFormat="short"
        isDateUnavailable={(date) =>
            !isSelectable(date)
        }
        class="w-full"
    >
        {#snippet children({ months, weekdays })}
            <Calendar.Header class="mb-5 flex items-center justify-between gap-3">
                <Calendar.PrevButton
                    class="rounded-3xl border border-(--border) bg-(--surface) px-4 py-2 text-sm font-semibold text-(--text) transition hover:bg-(--primary-soft) hover:text-(--primary)"
                >
                    Prev
                </Calendar.PrevButton>

                <Calendar.Heading
                    class="text-base font-semibold text-(--text)"
                />

                <Calendar.NextButton
                    class="rounded-3xl border border-(--border) bg-(--surface) px-4 py-2 text-sm font-semibold text-(--text) transition hover:bg-(--primary-soft) hover:text-(--primary)"
                >
                    Next
                </Calendar.NextButton>
            </Calendar.Header>

            {#each months as month}
                <Calendar.Grid
                    class="w-full border-collapse"
                >
                    <Calendar.GridHead>
                        <Calendar.GridRow
                            class="grid grid-cols-7 gap-1"
                        >
                            {#each weekdays as day}
                                <Calendar.HeadCell
                                    class="pb-2 text-center text-xs font-semibold text-(--text-muted)"
                                >
                                    {day}
                                </Calendar.HeadCell>
                            {/each}
                        </Calendar.GridRow>
                    </Calendar.GridHead>

                    <Calendar.GridBody>
                        {#each month.weeks as weekDates}
                            <Calendar.GridRow
                                class="grid grid-cols-7 gap-1"
                            >
                                {#each weekDates as date}
                                    {@const status =
                                        getStatus(date)}

                                    <Calendar.Cell
                                        {date}
                                        month={month.value}
                                    >
                                        <Calendar.Day
                                            class="
                                                flex h-10 w-10 items-center justify-center
                                                rounded-2xl text-sm font-semibold transition
                                                {STATUS_STYLES[status]}
                                                data-selected:border-(--primary)
                                                data-selected:bg-(--primary)
                                                data-selected:text-white
                                            "
                                        />
                                    </Calendar.Cell>
                                {/each}
                            </Calendar.GridRow>
                        {/each}
                    </Calendar.GridBody>
                </Calendar.Grid>
            {/each}
        {/snippet}
    </Calendar.Root>

    <div class="mt-5 grid grid-cols-2 gap-2 text-sm text-(--text-muted)">
        <div class="flex items-center gap-2">
            <span
                class={`h-3 w-3 rounded-full ${STATUS_STYLES[ServiceDayStatus.AVAILABLE]}`}
            ></span>

            <span>Available</span>
        </div>

        <div class="flex items-center gap-2">
            <span
                class={`h-3 w-3 rounded-full ${STATUS_STYLES[ServiceDayStatus.CLOSED]}`}
            ></span>

            <span>Closed</span>
        </div>

        <div class="col-span-2 flex items-center gap-2">
            <span
                class={`h-3 w-3 rounded-full ${STATUS_STYLES.UNAVAILABLE}`}
            ></span>

            <span>Unavailable</span>
        </div>
    </div>
</div>