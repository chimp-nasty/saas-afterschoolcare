<!--
    Admin › Families › a family: the parent's details (phone and address
    correctable), children and pickup people, bookings (with refunds),
    attendance history and payments, staff's notes about the children and
    messages to the family, in tabs.
-->
<script lang="ts">
    import Button from "$lib/components/actions/Button.svelte";
    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import { goto, invalidate } from "$app/navigation";
    import { page } from "$app/state";

    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";
    import AddNoteForm from "$lib/features/families/components/AddNoteForm.svelte";
    import FamilyAttendance from "$lib/features/families/components/FamilyAttendance.svelte";
    import FamilyBookings from "$lib/features/families/components/FamilyBookings.svelte";
    import FamilyDetails from "$lib/features/families/components/FamilyDetails.svelte";
    import FamilyMessages from "$lib/features/families/components/FamilyMessages.svelte";
    import FamilyNotes from "$lib/features/families/components/FamilyNotes.svelte";
    import FamilyPayments from "$lib/features/families/components/FamilyPayments.svelte";
    import SendMessageForm from "$lib/features/families/components/SendMessageForm.svelte";

    import { createFamiliesApi } from "$lib/api/public/adapters/families";
    import { createBookingApi } from "$lib/api/public/adapters/bookings";
    import { createRefundsApi } from "$lib/api/public/adapters/refunds";
    import type {
        ChildNoteResponse,
        CreateChildNoteRequest,
        FamilyBookingResponse,
        FamilyMessageResponse,
        SendFamilyMessageRequest,
        UpdateContactDetailsRequest
    } from "$lib/api/schema";
    import { messageFrame } from "$lib/features/families/message";
    import { familyTabs } from "$lib/navigation/tabs";
    import { formatDate, formatMoney, formatPhone } from "$lib/utils/helpers";

    let { data } = $props();

    const familiesApi = createFamiliesApi();
    const refundsApi = createRefundsApi();
    const bookingApi = createBookingApi();

    let activeTab = $state<string>(familyTabs.DETAILS);

    const tabs = [
        { id: familyTabs.DETAILS, label: "Details" },
        { id: familyTabs.BOOKINGS, label: "Bookings" },
        { id: familyTabs.ATTENDANCE, label: "Attendance" },
        { id: familyTabs.PAYMENTS, label: "Payments" },
        { id: familyTabs.NOTES, label: "Notes" },
        { id: familyTabs.MESSAGES, label: "Messages" }
    ];

    // Every message opens with the parent's name and ends with the centre's sign-off.
    const frame = $derived(
        messageFrame(
            data.family.first_name,
            data.location.location_name
        )
    );

    // Notes are about a current child.
    const currentChildren = $derived(data.family.children.filter((child) => child.is_active));

    let modal: Modal;
    let writing = $state<"note" | "message" | null>(null);

    function write(kind: "note" | "message") {
        writing = kind;
        modal.open();
    }

    async function addNote(body: CreateChildNoteRequest) {
        const response = await familiesApi.addNote(data.family.user_id, body);

        if (response.ok) {
            modal.close();
            await invalidate("app:family");
        }

        return response;
    }

    async function deleteNote(note: ChildNoteResponse) {
        await confirmAction({
            title: `Delete this note about ${note.child_first_name}?`,
            message: "Staff won't see it here or at the staff kiosk any more.",
            confirmLabel: "Delete",
            tone: "danger",
            action: async () => {
                if ((await familiesApi.deleteNote(data.family.user_id, note.id)).ok) await invalidate("app:family");
            }
        });
    }

    async function sendMessage(body: SendFamilyMessageRequest) {
        const response = await familiesApi.sendMessage(data.family.user_id, body);

        if (response.ok) {
            modal.close();
            await invalidate("app:family");
        }

        return response;
    }

    async function withdrawMessage(message: FamilyMessageResponse) {
        await confirmAction({
            title: `Withdraw "${message.title}"?`,
            message: "It's removed from the family's account. The email they were sent only said there was a message.",
            confirmLabel: "Withdraw",
            tone: "danger",
            action: async () => {
                if ((await familiesApi.withdrawMessage(data.family.user_id, message.id)).ok) await invalidate("app:family");
            }
        });
    }

    async function saveDetails(body: UpdateContactDetailsRequest) {
        const response = await familiesApi.update(data.family.user_id, body);

        if (response.ok) await invalidate("app:family");

        return response;
    }

    async function refund(booking: FamilyBookingResponse) {
        await confirmAction({
            title: `Refund ${booking.child_name}'s ${booking.service_name.toLowerCase()} on ${formatDate(booking.service_date)}?`,
            message: `${formatMoney(booking.price_snapshot_cents, booking.currency)} goes back to the card it was paid with, the booking is cancelled, and the family is emailed once Stripe confirms.`,
            confirmLabel: "Refund",
            tone: "danger",
            action: async () => {
                if ((await refundsApi.create(booking.id)).ok) await invalidate("app:family");
            }
        });
    }

    // Cancelling without a refund, and putting back: the family's own rules.
    async function cancelBooking(booking: FamilyBookingResponse) {
        await confirmAction({
            title: `Cancel ${booking.child_name}'s ${booking.service_name.toLowerCase()} on ${formatDate(booking.service_date)}?`,
            message: "It's after the family's refund cutoff, so nothing is refunded. The place is released, and it can be put back until the session starts if there's still a place. The family isn't emailed.",
            confirmLabel: "Cancel booking",
            tone: "danger",
            action: async () => {
                if ((await bookingApi.cancel(booking.id)).ok) await invalidate("app:family");
            }
        });
    }

    async function reinstateBooking(booking: FamilyBookingResponse) {
        await confirmAction({
            title: `Put back ${booking.child_name}'s ${booking.service_name.toLowerCase()} on ${formatDate(booking.service_date)}?`,
            message: "It's already paid for. It goes back on the run sheet if there's still a place. The family isn't emailed.",
            confirmLabel: "Put back",
            action: async () => {
                if ((await bookingApi.reinstate(booking.id)).ok) await invalidate("app:family");
            }
        });
    }

    // A list's date range, kept in the address.
    function setRange(prefix: "bookings" | "attendance", key: "from" | "to", value: string) {
        const params: Record<string, string> = { ...Object.fromEntries(page.url.searchParams), state: activeTab };

        if (value) params[`${prefix}_${key}`] = value;
        else delete params[`${prefix}_${key}`];

        void goto(`?${new URLSearchParams(params)}`, { keepFocus: true, noScroll: true });
    }
</script>

{#snippet range(prefix: "bookings" | "attendance", from: string | null, to: string | null, hint: string)}
    <div class="flex flex-wrap items-end gap-3">
        <label class="flex flex-col gap-1">
            <span class="label-text">From</span>
            <input type="date" value={from ?? ""} onchange={(event) => setRange(prefix, "from", event.currentTarget.value)} />
        </label>
        <label class="flex flex-col gap-1">
            <span class="label-text">To</span>
            <input type="date" value={to ?? ""} onchange={(event) => setRange(prefix, "to", event.currentTarget.value)} />
        </label>
        <p class="text-sm text-(--text-muted)">{hint}</p>
    </div>
{/snippet}

<Page width="wide">
    <ActionBar start>
        <Button variant="ghost" onclick={() => goto(`/${data.locationCode}/admin/families`)}>Back to families</Button>
    </ActionBar>

    <PageHeader
        title={`${data.family.first_name} ${data.family.last_name}`}
        description={[data.family.email, data.family.phone ? formatPhone(data.family.phone) : null].filter(Boolean).join(" · ")}
    />

    <TabbedPanels {tabs} bind:activeTab queryParam="state">
        {#snippet panel(id)}
            {#if id === familyTabs.DETAILS}
                <FamilyDetails family={data.family} locationCode={data.locationCode} onsubmit={saveDetails} />
            {:else if id === familyTabs.BOOKINGS}
                <div class="flex flex-col gap-4">
                    {@render range("bookings", data.ranges.bookingsFrom, data.ranges.bookingsTo, "Default: a month back to three months ahead. Bookings awaiting payment always show.")}
                    <FamilyBookings bookings={data.bookings} onrefund={refund} oncancel={cancelBooking} onreinstate={reinstateBooking} />
                </div>
            {:else if id === familyTabs.ATTENDANCE}
                <div class="flex flex-col gap-4">
                    {@render range("attendance", data.ranges.attendanceFrom, data.ranges.attendanceTo, "Default: the last 4 weeks.")}
                    <FamilyAttendance entries={data.attendance} />
                </div>
            {:else if id === familyTabs.PAYMENTS}
                <FamilyPayments payments={data.payments} />
            {:else if id === familyTabs.NOTES}
                <FamilyNotes notes={data.notes} canAdd={currentChildren.length > 0} onadd={() => write("note")} ondelete={deleteNote} />
            {:else if id === familyTabs.MESSAGES}
                <FamilyMessages messages={data.messages} onsend={() => write("message")} onwithdraw={withdrawMessage} />
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>

<Modal
    bind:this={modal}
    title={writing === "note" ? "Add a note" : "Send a message"}
    description={writing === "note"
        ? "Only staff see notes, here and at the staff kiosk."
        : `To ${data.family.first_name} ${data.family.last_name}, in their account.`}
    onclose={() => { writing = null; }}
>
    {#if writing === "note"}
        <AddNoteForm kids={currentChildren} onsubmit={addNote} />
    {:else if writing === "message"}
        <SendMessageForm kids={currentChildren} {frame} onsubmit={sendMessage} />
    {/if}
</Modal>
