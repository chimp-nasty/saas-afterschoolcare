<script lang="ts">
    import { goto } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import CustomerBookings from "./CustomerBookings.svelte";

    type Booking = {
        id: string;
        serviceDate: string;
        serviceCode: string;
        serviceLabel: string;
        childId: string;
        childFirstName: string;
    };

    let {
        bookings,
        locationCode
    }: {
        bookings: Booking[];
        locationCode: string;
    } = $props();
</script>

<div class="flex flex-1 flex-col justify-between gap-4">
    <CustomerBookings {bookings} />

    <Button
        fullWidth
        onclick={() => goto(`/${locationCode}/bookings/new`)}
    >
        Book Now
    </Button>
</div>