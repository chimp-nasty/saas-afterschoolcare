<!--
    Pick the days to book. Each day shows whether it can be booked for the
    children currently selected: already booked for one of them, or not
    enough places, shows red and can't be picked; few places left shows
    amber with how many; past days are greyed out. The backend checks all of
    this again when booking.
-->
<script lang="ts">
    import { untrack } from "svelte";
    import { Calendar } from "bits-ui";
    import { ChevronLeft, ChevronRight, Minus, X } from "lucide-svelte";
    import { parseDate, type DateValue } from "@internationalized/date";
    import { toast } from "svelte-sonner";

    import Card from "$lib/components/layout/Card.svelte";

    import type { LocationServiceDayTableResponse } from "$lib/api/schema";
    import { formatDate } from "$lib/utils/helpers";
    import { LOW_PLACES_THRESHOLD, ServiceDayStatus } from "../types";

    let {
        serviceDays,
        selectedChildIds,
        childNames,
        selectedDates = $bindable([]),
    }: {
        serviceDays: LocationServiceDayTableResponse[];
        selectedChildIds: string[];
        // First names by child id, for saying who's already booked.
        childNames: Record<string, string>;
        selectedDates: string[];
    } = $props();

    // Starts from the parent's dates (e.g. coming back from review); after
    // that the user's clicks change it (onValueChange), or a date dropped
    // below when it stops being bookable.
    let selected = $state<DateValue[]>(
        untrack(() => selectedDates.map((date) => parseDate(date)))
    );

    const dayMap = $derived(
        new Map(serviceDays.map((serviceDay) => [serviceDay.service_date, serviceDay]))
    );

    function bookedChildIds(serviceDay: LocationServiceDayTableResponse): string[] {
        return serviceDay.booked_child_ids.filter((id) => selectedChildIds.includes(id));
    }

    function getStatus(dateKey: string): ServiceDayStatus {
        const serviceDay = dayMap.get(dateKey);

        if (!serviceDay) {
            return ServiceDayStatus.UNAVAILABLE;
        }

        if (serviceDay.is_past) {
            return ServiceDayStatus.PAST;
        }

        if (!serviceDay.is_open) {
            return ServiceDayStatus.CLOSED;
        }

        if (bookedChildIds(serviceDay).length > 0) {
            return ServiceDayStatus.BOOKED;
        }

        // Every selected child needs a place.
        if (serviceDay.places_left < Math.max(selectedChildIds.length, 1)) {
            return ServiceDayStatus.FULL;
        }

        if (serviceDay.places_left <= LOW_PLACES_THRESHOLD) {
            return ServiceDayStatus.LOW;
        }

        return ServiceDayStatus.AVAILABLE;
    }

    function isSelectable(dateKey: string): boolean {
        const status = getStatus(dateKey);

        return status === ServiceDayStatus.AVAILABLE || status === ServiceDayStatus.LOW;
    }

    // Why a day can't be booked (or how full it is), in words: for screen
    // readers on each day, and the message when a picked date is dropped.
    function describe(dateKey: string): string | null {
        const serviceDay = dayMap.get(dateKey);

        switch (getStatus(dateKey)) {
            case ServiceDayStatus.BOOKED: {
                const names = bookedChildIds(serviceDay!).map((id) => childNames[id] ?? "A child");
                return `${names.join(" and ")} ${names.length === 1 ? "is" : "are"} already booked`;
            }
            case ServiceDayStatus.FULL:
                return "there aren't enough places";
            case ServiceDayStatus.LOW:
                return `${serviceDay!.places_left} ${serviceDay!.places_left === 1 ? "place" : "places"} left`;
            case ServiceDayStatus.PAST:
                return "the day has passed";
            default:
                return null;
        }
    }

    // Changing the children can make a picked date unbookable (one of them
    // is already booked, or there aren't places for everyone): drop it and
    // say why, rather than letting the booking fail later.
    $effect(() => {
        const removed = selectedDates.filter((date) => !isSelectable(date));

        if (removed.length === 0) {
            return;
        }

        untrack(() => {
            selectedDates = selectedDates.filter((date) => isSelectable(date));
            selected = selectedDates.map((date) => parseDate(date));

            const reason = removed.length === 1
                ? describe(removed[0])
                : "a selected child is already booked, or there aren't enough places";

            toast.info(`Removed ${removed.map(formatDate).join(", ")}: ${reason}.`);
        });
    });

    const STATUS_STYLES: Record<ServiceDayStatus, string> = {
        [ServiceDayStatus.AVAILABLE]:
            "border border-(--success)/20 bg-(--success-soft) text-(--success-text) hover:bg-(--secondary-soft)",

        [ServiceDayStatus.LOW]:
            "border border-(--warning)/40 bg-(--warning-soft) text-(--warning-text) hover:brightness-95",

        [ServiceDayStatus.BOOKED]:
            "border border-(--danger) bg-(--danger-soft) text-(--danger-text) cursor-not-allowed",

        [ServiceDayStatus.FULL]:
            "border border-(--danger)/40 bg-(--danger-soft) text-(--danger-text) cursor-not-allowed",

        [ServiceDayStatus.CLOSED]:
            "border border-(--border) bg-(--surface) text-(--text-muted) opacity-70 cursor-not-allowed",

        [ServiceDayStatus.PAST]:
            "border border-transparent bg-(--surface-muted) text-(--text-muted) opacity-50 cursor-not-allowed",

        [ServiceDayStatus.UNAVAILABLE]:
            "border border-transparent bg-transparent text-(--text-muted) opacity-30 cursor-not-allowed",
    };

    // Past and "no session" days explain themselves (greyed, can't be tapped).
    const LEGEND = [
        { status: ServiceDayStatus.AVAILABLE, label: "Available" },
        { status: ServiceDayStatus.LOW, label: "Few places left" },
        { status: ServiceDayStatus.BOOKED, label: "Already booked" },
        { status: ServiceDayStatus.FULL, label: "Full" },
        { status: ServiceDayStatus.CLOSED, label: "Closed" },
    ];
</script>

<Card border>
    <Calendar.Root
        type="multiple"
        bind:value={selected}
        onValueChange={(value) => {
            selectedDates = value.map((date) => date.toString());
        }}
        weekdayFormat="short"
        isDateUnavailable={(date) => !isSelectable(date.toString())}
        class="w-full"
    >
        {#snippet children({ months, weekdays })}
            <Calendar.Header class="mb-5 flex items-center justify-between gap-3">
                <Calendar.PrevButton
                    class="flex h-11 w-11 items-center justify-center rounded-lg border border-(--border) bg-(--surface) text-(--text) transition hover:bg-(--primary-soft) hover:text-(--primary)"
                    aria-label="Previous month"
                >
                    <ChevronLeft size={20} />
                </Calendar.PrevButton>

                <Calendar.Heading
                    class="text-lg font-extrabold text-(--text)"
                />

                <Calendar.NextButton
                    class="flex h-11 w-11 items-center justify-center rounded-lg border border-(--border) bg-(--surface) text-(--text) transition hover:bg-(--primary-soft) hover:text-(--primary)"
                    aria-label="Next month"
                >
                    <ChevronRight size={20} />
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
                                    class="pb-2 text-center label-text"
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
                                    {@const dateKey = date.toString()}
                                    {@const status = getStatus(dateKey)}
                                    {@const description = describe(dateKey)}

                                    <Calendar.Cell
                                        {date}
                                        month={month.value}
                                    >
                                        <Calendar.Day
                                            class="
                                                flex h-12 w-full flex-col items-center justify-center gap-0.5
                                                rounded-lg text-sm font-semibold transition
                                                {STATUS_STYLES[status]}
                                                data-selected:border-(--primary)
                                                data-selected:bg-(--primary)
                                                data-selected:text-white
                                            "
                                        >
                                            {#snippet children({ day })}
                                                <span>{day}</span>

                                                {#if status === ServiceDayStatus.LOW}
                                                    <span class="text-xs leading-none">
                                                        {dayMap.get(dateKey)?.places_left} left
                                                    </span>
                                                {:else if status === ServiceDayStatus.BOOKED}
                                                    <X size={12} aria-hidden="true" />
                                                {:else if status === ServiceDayStatus.FULL}
                                                    <Minus size={12} aria-hidden="true" />
                                                {/if}

                                                {#if description}
                                                    <span class="sr-only">{description}</span>
                                                {/if}
                                            {/snippet}
                                        </Calendar.Day>
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
        {#each LEGEND as item (item.status)}
            <div class="flex items-center gap-2">
                <span class={`flex h-4 w-4 items-center justify-center rounded-full ${STATUS_STYLES[item.status]}`}>
                    {#if item.status === ServiceDayStatus.BOOKED}
                        <X size={10} aria-hidden="true" />
                    {:else if item.status === ServiceDayStatus.FULL}
                        <Minus size={10} aria-hidden="true" />
                    {/if}
                </span>

                <span>{item.label}</span>
            </div>
        {/each}
    </div>
</Card>
