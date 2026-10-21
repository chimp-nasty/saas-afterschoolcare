<!--
    Admin › Service days: a service's days for a month, each open or closed
    with its places, bookings and places left. Admins see it; superadmins
    (by permission) add days, change places, close, reopen and delete them.
    The database keeps bookings safe whoever does it.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";
    import { toast } from "svelte-sonner";

    import Button from "$lib/components/actions/Button.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import AddServiceDaysForm from "$lib/features/services/components/AddServiceDaysForm.svelte";
    import EditServiceDayForm from "$lib/features/services/components/EditServiceDayForm.svelte";
    import ServiceDayCapacityForm from "$lib/features/services/components/ServiceDayCapacityForm.svelte";

    import { auth } from "$lib/auth/state.svelte";
    import { createLocationServiceDaysApi } from "$lib/api/public/adapters/location-service-days";
    import type {
        CreateServiceDaysRequest,
        ServiceDayOverviewResponse,
        SetServiceDayCapacityRequest,
        UpdateServiceDayRequest
    } from "$lib/api/schema";
    import { formatDate } from "$lib/utils/helpers";

    let { data } = $props();

    const daysApi = createLocationServiceDaysApi();

    // Changing days is the superadmins' (the API refuses admins too).
    const canChange = $derived($auth.roles.includes("superadmin"));

    const service = $derived(data.services.find((s) => s.id === data.serviceId) ?? null);

    const monthLabel = $derived(
        new Date(`${data.month}-01T00:00:00Z`).toLocaleDateString("en-AU", { month: "long", year: "numeric", timeZone: "UTC" })
    );

    function shiftMonth(months: number): string {
        const [year, month] = data.month.split("-").map(Number);
        const shifted = new Date(Date.UTC(year, month - 1 + months, 1));

        return `${shifted.getUTCFullYear()}-${String(shifted.getUTCMonth() + 1).padStart(2, "0")}`;
    }

    function show(params: { service?: string; month?: string }) {
        const query = new URLSearchParams({
            service: params.service ?? data.serviceId ?? "",
            month: params.month ?? data.month
        });

        void goto(`?${query}`, { keepFocus: true, noScroll: true });
    }

    let modal: Modal;
    let mode = $state<"add" | "add-one" | "capacity" | "edit" | null>(null);
    let editing = $state<ServiceDayOverviewResponse | null>(null);

    const title = $derived(
        mode === "add" ? "Add days" : mode === "add-one" ? "Add one day" : mode === "capacity" ? "Change places" : editing ? formatDate(editing.service_date) : ""
    );

    function open(next: typeof mode, day: ServiceDayOverviewResponse | null = null) {
        mode = next;
        editing = day;
        modal.open();
    }

    async function done() {
        modal.close();
        await invalidate("app:service-days");
    }

    async function addDays(body: Omit<CreateServiceDaysRequest, "location_service_id">) {
        const response = await daysApi.create({ ...body, location_service_id: data.serviceId! });

        if (response.ok && response.data) {
            if (response.data.skipped.length) {
                toast.info(`${response.data.skipped.length} days were already there and weren't changed.`);
            }
            await done();
        }

        return response;
    }

    async function setCapacity(body: Omit<SetServiceDayCapacityRequest, "location_service_id">) {
        const response = await daysApi.setCapacity({ ...body, location_service_id: data.serviceId! });

        if (response.ok) await done();

        return response;
    }

    async function updateDay(body: UpdateServiceDayRequest) {
        const response = await daysApi.update(editing!.id, body);

        if (response.ok) await done();

        return response;
    }

    async function deleteDay() {
        const day = editing!;

        await confirmAction({
            title: `Delete ${formatDate(day.service_date)}?`,
            message: "The day is removed. It's never been booked, so no family is affected.",
            confirmLabel: "Delete",
            tone: "danger",
            action: async () => {
                const response = await daysApi.remove(day.id);

                if (response.ok) await done();
            }
        });
    }

    const columns = "grid grid-cols-[minmax(9rem,1.4fr)_minmax(9rem,1.4fr)_5rem_5rem_7rem_6rem_6rem] items-center gap-x-4";
</script>

<Page width="wide">
    <PageHeader
        title="Service days"
        description="Each day a service runs, and its places. Families can only book open days with places left."
    />

    <div class="flex flex-wrap items-end justify-between gap-4">
        <div class="flex flex-wrap items-end gap-3">
            <label class="flex flex-col gap-1">
                <span class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Service</span>
                <select value={data.serviceId} onchange={(event) => show({ service: event.currentTarget.value })}>
                    {#each data.services as option (option.id)}
                        <option value={option.id}>{option.service_name}</option>
                    {/each}
                </select>
            </label>

            <Button variant="ghost" onclick={() => show({ month: shiftMonth(-1) })}>Previous month</Button>
            <p class="min-w-40 text-center text-lg font-extrabold text-(--text)">{monthLabel}</p>
            <Button variant="ghost" onclick={() => show({ month: shiftMonth(1) })}>Next month</Button>
        </div>

        {#if canChange && service}
            <div class="flex flex-wrap gap-3">
                <Button variant="ghost" onclick={() => open("capacity")}>Change places</Button>
                <Button variant="ghost" onclick={() => open("add-one")}>Add one day</Button>
                <Button onclick={() => open("add")}>Add days</Button>
            </div>
        {/if}
    </div>

    {#if !service}
        <p class="text-base text-(--text-muted)">No services are offered yet.</p>
    {:else}
        <div class="overflow-x-auto rounded-2xl border border-(--border) bg-(--surface)">
            <div class="min-w-[52rem]" role="table" aria-label={`${service.service_name} days`}>
                <div class={[columns, "border-b border-(--border) bg-(--surface-muted) px-5 py-2"]} role="row">
                    {#each ["Date", "Status", "Places", "Booked", "Awaiting pay", "Left", ""] as header, index (index)}
                        <span class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)" role="columnheader">{header}</span>
                    {/each}
                </div>

                {#each data.days as day (day.id)}
                    <div
                        class={[columns, "min-h-12 border-b border-(--border) px-5 py-2 last:border-b-0", day.is_past && "opacity-60"]}
                        role="row"
                    >
                        <span class="text-base font-semibold text-(--text)" role="cell">{formatDate(day.service_date)}</span>
                        <span class="truncate text-base text-(--text)" role="cell">
                            {#if day.is_open}
                                Open
                            {:else}
                                <span class="font-semibold text-(--warning-text)">Closed</span>{#if day.closed_reason}<span class="text-(--text-muted)"> · {day.closed_reason}</span>{/if}
                            {/if}
                        </span>
                        <span class="text-base text-(--text)" role="cell">{day.capacity}</span>
                        <span class="text-base text-(--text)" role="cell">{day.booked}</span>
                        <span class="text-base text-(--text-muted)" role="cell">{day.awaiting_payment}</span>
                        <span class={["text-base", day.places_left === 0 && day.is_open ? "font-extrabold text-(--danger-text)" : "text-(--text)"]} role="cell">
                            {day.is_open ? (day.places_left === 0 ? "Full" : day.places_left) : "—"}
                        </span>
                        <span role="cell">
                            {#if canChange && !day.is_past}
                                <Button variant="ghost" fullWidth onclick={() => open("edit", day)}>Edit</Button>
                            {/if}
                        </span>
                    </div>
                {:else}
                    <p class="px-5 py-3 text-base text-(--text-muted)">
                        No {service.service_name.toLowerCase()} days in {monthLabel}.{#if canChange} Use Add days to set them up.{/if}
                    </p>
                {/each}
            </div>
        </div>
    {/if}
</Page>

<Modal bind:this={modal} {title} onclose={() => { mode = null; editing = null; }}>
    {#if mode === "add"}
        <AddServiceDaysForm onsubmit={addDays} />
    {:else if mode === "add-one"}
        <AddServiceDaysForm single onsubmit={addDays} />
    {:else if mode === "capacity"}
        <ServiceDayCapacityForm onsubmit={setCapacity} />
    {:else if mode === "edit" && editing}
        <EditServiceDayForm
            day={editing}
            onsubmit={updateDay}
            ondelete={editing.ever_booked ? undefined : deleteDay}
        />
    {/if}
</Modal>
