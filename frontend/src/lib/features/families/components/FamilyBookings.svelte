<!--
    A family's bookings in Admin › Families: date, child, service, booking
    and payment status, price, and what an admin can do: Refund a paid
    booking (up to and including the session day; one booking, in full),
    and, under the family's own rules (after their refund cutoff, until
    the session starts), Cancel it without a refund or Put back one
    cancelled that way. A date range picks which; anything awaiting
    payment always shows.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import GridTable from '$lib/components/layout/GridTable.svelte';

	import type { FamilyBookingResponse } from '$lib/api/schema';
	import { BOOKING_STATUS_LABELS } from '$lib/features/bookings/status';
	import { paymentLabel } from '$lib/features/kiosk/bookings';
	import { formatDate, formatMoney } from '$lib/utils/helpers';

	let {
		bookings,
		onrefund,
		oncancel,
		onreinstate
	}: {
		bookings: FamilyBookingResponse[];
		onrefund: (booking: FamilyBookingResponse) => void;
		oncancel: (booking: FamilyBookingResponse) => void;
		onreinstate: (booking: FamilyBookingResponse) => void;
	} = $props();

	function refundable(booking: FamilyBookingResponse): boolean {
		return booking.is_refundable_by_admin && booking.payment_status === 'PAID' && booking.refund_status !== 'PENDING';
	}

	const columns = 'minmax(8rem,1fr) minmax(9rem,1.2fr) minmax(10rem,1.3fr) 8rem minmax(9rem,1fr) 6rem 15rem';
</script>

<GridTable
	items={bookings}
	key={(booking) => booking.id}
	{columns}
	headers={['Date', 'Child', 'Service', 'Booking', 'Payment', 'Price', '']}
	label="Bookings"
	minWidth="64rem"
	maxRows={12}
	empty="No bookings in this range."
>
	{#snippet row(booking)}
		<span class="text-base font-semibold text-(--text)" role="cell">{formatDate(booking.service_date)}</span>
		<span class="text-base text-(--text)" role="cell">{booking.child_name}</span>
		<span class="text-base text-(--text)" role="cell">{booking.service_name}</span>
		<span class="text-base text-(--text)" role="cell">{BOOKING_STATUS_LABELS[booking.booking_status]}</span>
		<span class={['text-base', booking.payment_status === 'PENDING' ? 'font-semibold text-(--warning-text)' : 'text-(--text)']} role="cell">
			{paymentLabel(booking)}
		</span>
		<span class="text-base text-(--text)" role="cell">{formatMoney(booking.price_snapshot_cents, booking.currency)}</span>
		<span class="flex gap-2" role="cell">
			{#if refundable(booking)}
				<Button variant="ghost" width="w-32" onclick={() => onrefund(booking)}>Refund</Button>
			{/if}
			{#if booking.is_cancellable}
				<Button variant="ghost" width="w-32" onclick={() => oncancel(booking)}>Cancel</Button>
			{:else if booking.is_reinstatable}
				<Button variant="ghost" width="w-32" onclick={() => onreinstate(booking)}>Put back</Button>
			{/if}
		</span>
	{/snippet}
</GridTable>
