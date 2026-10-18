<script lang="ts">
    import { goto } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import CustomerBookings from "./CustomerBookings.svelte";

    import type { BookingTableResponse } from "$lib/api/schema";

    let {
        bookings,
        locationCode
    }: {
        bookings: BookingTableResponse[];
        locationCode: string;
    } = $props();
</script>

<div class="flex flex-1 flex-col justify-between gap-4">
    <CustomerBookings {bookings} {locationCode} />

    <Button
        fullWidth
        onclick={() => goto(`/${locationCode}/bookings/new`)}
    >
        Book Now
    </Button>
</div>
