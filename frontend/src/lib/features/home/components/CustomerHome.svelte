<script lang="ts">
    import { goto } from "$app/navigation";
    import { page } from "$app/state";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import SectionHeading from "$lib/components/text/SectionHeading.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import CentreCard from "$lib/features/location/components/CentreCard.svelte";
    import CentreMap from "$lib/features/location/components/CentreMap.svelte";
    import CustomerBookings from "./CustomerBookings.svelte";
    import NewMessagesModal from "$lib/features/actions/components/NewMessagesModal.svelte";

    import { auth } from "$lib/auth/state.svelte";
    import type { BookingTableResponse, PublicLocationResponse } from "$lib/api/schema";
    import { setupHref, type SetupProgress } from "$lib/features/customer/setup";

    let {
        bookings,
        locationCode,
        location,
        setup
    }: {
        bookings: BookingTableResponse[];
        locationCode: string;
        location: PublicLocationResponse;
        // Null when it couldn't be loaded: no card.
        setup: SetupProgress | null;
    } = $props();

    function toDateKey(date: Date): string {
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, "0");
        const day = String(date.getDate()).padStart(2, "0");

        return `${year}-${month}-${day}`;
    }

    // This calendar week (Monday to Sunday), as date strings so they compare
    // with service_date directly.
    const today = new Date();
    const todayKey = toDateKey(today);

    const monday = new Date(today);
    monday.setDate(today.getDate() - ((today.getDay() + 6) % 7));

    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);

    const mondayKey = toDateKey(monday);
    const sundayKey = toDateKey(sunday);

    // The loader only returns pending and confirmed bookings.
    const thisWeek = $derived(
        bookings.filter(
            (booking) =>
                booking.service_date >= mondayKey &&
                booking.service_date <= sundayKey
        )
    );

    // Today counts as upcoming.
    const upcomingCount = $derived(
        thisWeek.filter((booking) => booking.service_date >= todayKey).length
    );

    const weekSummary = $derived.by(() => {
        if (thisWeek.length === 0) {
            return "You have no bookings this week.";
        }

        if (upcomingCount === 0) {
            return "You have no more upcoming bookings this week.";
        }

        return upcomingCount === 1
            ? "You have 1 upcoming booking this week."
            : `You have ${upcomingCount} upcoming bookings this week.`;
    });
</script>

<PageHeader
    title={$auth.firstName ? `Hi ${$auth.firstName}` : "Welcome"}
    description={weekSummary}
/>

<!-- Until the family has what booking needs: back into setup where they
     left off. -->
{#if setup?.next}
    <Card border>
        <div class="flex flex-col gap-4">
            <SectionHeading
                title="Finish setting up"
                description={`${setup.done} of ${setup.total} done. You'll need the rest before you can book.`}
            />

            <ActionBar start>
                <Button onclick={() => goto(setupHref(locationCode, setup.next ?? undefined))}>Continue setup</Button>
            </ActionBar>
        </div>
    </Card>
{/if}

<Card border>
    <CustomerBookings {bookings} {locationCode} />
</Card>

<Button
    fullWidth
    onclick={() => goto(`/${locationCode}/bookings/new`)}
>
    Book now
</Button>

<!-- The "running late" number, one tap from the main screen, and where
     the centre is. -->
<CentreCard {location} />

<CentreMap {location} compact />

<NewMessagesModal
    count={page.data.uncitedActionCount ?? 0}
    messagesHref={`/${locationCode}/actions`}
/>
