<!--
    The admin run sheet: the same view as the staff kiosk's Run sheet tab
    (a tab per service, places, who signed each child in and out), read-only:
    nothing here changes attendance, which happens only at the kiosks. Any
    day can be shown, and each service's sheet printed.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";
    import { onDestroy, onMount, tick } from "svelte";
    import { page } from "$app/state";

    import Button from "$lib/components/actions/Button.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import ErrorText from "$lib/components/text/ErrorText.svelte";
    import PrintableRunSheet, { type PrintSession } from "$lib/features/attendance/components/PrintableRunSheet.svelte";
    import StaffRoll from "$lib/features/kiosk/components/StaffRoll.svelte";
    import { ROLL_REFRESH_MS } from "$lib/features/kiosk/kiosk";
    import type { RunSheetSessionResponse } from "$lib/api/schema";
    import { formatDate } from "$lib/utils/helpers";

    let { data } = $props();

    const date = $derived(data.board?.date ?? "");

    // The location's today, from the last load without a day (kept while
    // other days are shown).
    let today = $state("");
    $effect(() => {
        if (data.today) today = data.today;
    });

    // A YYYY-MM-DD date `days` away, without going through local time.
    function shift(value: string, days: number): string {
        const day = new Date(`${value}T00:00:00Z`);
        day.setUTCDate(day.getUTCDate() + days);

        return day.toISOString().slice(0, 10);
    }

    function show(value: string) {
        void goto(`?date=${value}`, { keepFocus: true, noScroll: true });
    }

    let printSessions = $state<PrintSession[] | null>(null);

    // One service's printed sheet, from the roll (pickup lists and phones).
    async function print(session: RunSheetSessionResponse) {
        printSessions = [
            {
                name: session.service_name,
                startTime: session.start_time,
                endTime: session.end_time,
                entries: (data.roll?.entries ?? []).filter(
                    (entry) => entry.service_name === session.service_name && entry.start_time === session.start_time
                )
            }
        ];

        await tick();
        // Cleared on afterprint: on some tablets print() returns straight away.
        window.print();
    }

    function afterPrint() {
        printSessions = null;
    }

    let refresher: ReturnType<typeof setInterval> | null = null;

    onMount(() => {
        refresher = setInterval(() => void invalidate("app:attendance-roll"), ROLL_REFRESH_MS);
        window.addEventListener("afterprint", afterPrint);
    });

    onDestroy(() => {
        if (refresher) clearInterval(refresher);
        window.removeEventListener("afterprint", afterPrint);
    });
</script>

<Page width="wide">
    <PageHeader
        title="Run sheet"
        description="Who's booked, here and gone, as the staff kiosk shows it. Signing in and out, ID checks and corrections are done at the staff kiosk."
    />

    <div class="flex flex-wrap items-end gap-3">
        <Button variant="ghost" isDisabled={!date} onclick={() => show(shift(date, -1))}>Previous day</Button>

        <label class="flex flex-col gap-1">
            <span class="label-text">Day</span>
            <input type="date" value={date} onchange={(event) => show(event.currentTarget.value)} />
        </label>

        <Button variant="ghost" isDisabled={!date} onclick={() => show(shift(date, 1))}>Next day</Button>

        {#if date}
            <p class="text-sm text-(--text-muted)">{formatDate(date)}</p>
        {/if}
    </div>

    {#if data.boardError}
        <ErrorText message={data.boardError} />
    {:else if data.board}
        <!-- A new day picks its default session tab again. -->
        {#key date}
            <StaffRoll
                sessions={data.board.sessions}
                entries={data.board.entries}
                isToday={!!today && date === today}
                isPast={!!today && date < today}
                onprint={print}
                size="web"
            />
        {/key}
    {/if}
</Page>

{#if printSessions && data.roll}
    <PrintableRunSheet
        centreName={page.data.location?.name ?? page.data.locationCode}
        date={data.roll.date}
        sessions={printSessions}
        families={data.roll.families}
    />
{/if}
