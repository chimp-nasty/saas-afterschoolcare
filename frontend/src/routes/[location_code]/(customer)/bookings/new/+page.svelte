<script lang="ts">
    import CreateBookingFlow from "$lib/features/bookings/components/CreateBookingFlow.svelte";

    let { data } = $props();

    function handleConfirm() {
        // booking mutation will live here later
    }
</script>

<CreateBookingFlow
    locationServices={data.locationServices}
    children={data.children}
    serviceDays={data.serviceDays}
    onConfirm={handleConfirm}
/>