<script lang="ts">
    import { goto } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import CustomerBookings from "./CustomerBookings.svelte";

    import { auth } from "$lib/auth/state.svelte";
    import type { BookingTableResponse } from "$lib/api/schema";

    let {
        bookings,
        locationCode
    }: {
        bookings: BookingTableResponse[];
        locationCode: string;
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

<Card border>
    <CustomerBookings {bookings} {locationCode} />
</Card>

<Button
    fullWidth
    onclick={() => goto(`/${locationCode}/bookings/new`)}
>
    Book now
</Button>
