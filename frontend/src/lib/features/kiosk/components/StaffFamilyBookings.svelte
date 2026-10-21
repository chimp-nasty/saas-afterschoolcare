<!--
    A family's bookings at the staff kiosk: today to 2 weeks ahead, and
    anything still awaiting payment. Read-only in a child's panel; in an
    admin's refund, each booking an admin can still refund (paid, up to and
    including its day) has Refund. One booking is one child on one day,
    refunded in full.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';

	import type { FamilyBookingResponse } from '$lib/api/schema';
	import { BOOKING_STATUS_LABELS } from '$lib/features/bookings/status';
	import { formatDate, formatMoney } from '$lib/utils/helpers';
	import { paymentLabel } from '../bookings';

	let {
		bookings,
		error,
		busy = false,
		onrefund
	}: {
		bookings: FamilyBookingResponse[] | null;
		error: string | null;
		busy?: boolean;
		// Only in an admin's refund.
		onrefund?: (booking: FamilyBookingResponse) => void;
	} = $props();

	function refundable(booking: FamilyBookingResponse): boolean {
		return booking.is_refundable_by_admin && booking.payment_status === 'PAID' && booking.refund_status !== 'PENDING';
	}
</script>

{#if error}
	<p class="text-lg font-semibold text-(--danger-text)" role="alert">{error}</p>
{:else if !bookings}
	<p class="text-base text-(--text-muted)">Loading bookings…</p>
{:else}
	<div class="flex flex-col gap-2">
		<p class="text-sm text-(--text-muted)">Today to 2 weeks ahead, and anything awaiting payment.</p>

		<ul class="flex max-h-[45vh] flex-col overflow-y-auto rounded-lg border border-(--border)">
			{#each bookings as booking (booking.id)}
				<li class="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-(--border) px-4 py-2 last:border-b-0">
					<div class="min-w-0">
						<p class="text-base font-semibold text-(--text)">
							{formatDate(booking.service_date)} · {booking.child_name}
						</p>
						<p class="text-sm text-(--text-muted)">
							{booking.service_name} · {BOOKING_STATUS_LABELS[booking.booking_status]} ·
							<span class={booking.payment_status === 'PENDING' ? 'font-semibold text-(--warning-text)' : ''}>
								{paymentLabel(booking)}
							</span>
							· {formatMoney(booking.price_snapshot_cents, booking.currency)}
						</p>
					</div>

					{#if onrefund && refundable(booking)}
						<Button variant="ghost" isDisabled={busy} onclick={() => onrefund(booking)}>Refund</Button>
					{/if}
				</li>
			{:else}
				<li class="px-4 py-3 text-base text-(--text-muted)">No bookings in that time.</li>
			{/each}
		</ul>
	</div>
{/if}
