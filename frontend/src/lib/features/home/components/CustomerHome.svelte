<script lang="ts">
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

    let { bookings }: { bookings: Booking[]; } = $props();
</script>

<div class="flex flex-1 flex-col justify-between gap-4">
	<CustomerBookings {bookings} />

	<Button fullWidth>
		Book Now
	</Button>
</div>