<!--
    Today's sessions for the children a pickup person may collect, one tile
    each, with the single next step for that session. When the centre only
    allows signing around each session (2 hours either side), the tile says
    when it opens, or to see a staff member once it's closed, instead of a
    button that would be refused.
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';

	import type { KioskBookingResponse } from '$lib/api/schema';
	import { formatTimeRange } from '$lib/utils/helpers';
	import { formatClock } from '../kiosk';

	let {
		bookings,
		busyBookingId = null,
		onsign
	}: {
		bookings: KioskBookingResponse[];
		busyBookingId?: string | null;
		onsign: (booking: KioskBookingResponse, action: 'in' | 'out') => void;
	} = $props();

	let now = $state(Date.now());
	let ticker: ReturnType<typeof setInterval> | null = null;

	function notYetOpen(booking: KioskBookingResponse): boolean {
		return !!booking.signing_opens_at && now < Date.parse(booking.signing_opens_at);
	}

	function closed(booking: KioskBookingResponse): boolean {
		return !!booking.signing_closes_at && now > Date.parse(booking.signing_closes_at);
	}

	onMount(() => {
		ticker = setInterval(() => (now = Date.now()), 15_000);
	});

	onDestroy(() => {
		if (ticker) clearInterval(ticker);
	});
</script>

<div class="flex flex-col gap-4">
	{#each bookings as booking (booking.booking_id)}
		<Card border>
			<div class="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
				<div class="flex flex-col gap-1">
					<p class="text-2xl font-extrabold text-(--text)">
						{booking.child_first_name} {booking.child_last_initial}.
					</p>
					<p class="text-base text-(--text-muted)">
						{booking.service_name} · {formatTimeRange(booking.start_time, booking.end_time)}
					</p>

					{#if booking.signed_out_at}
						<p class="text-lg font-semibold text-(--success-text)">✓ Signed out {formatClock(booking.signed_out_at)}</p>
					{:else if booking.signed_in_at}
						<p class="text-lg font-semibold text-(--text)">Signed in {formatClock(booking.signed_in_at)}</p>
					{/if}
				</div>

				<div class="md:w-56">
					{#if booking.signed_out_at}
						<!-- Done for today. -->
					{:else if !booking.signed_in_at && notYetOpen(booking) && booking.signing_opens_at}
						<p class="text-lg font-semibold text-(--text-muted)">
							Sign in opens at {formatClock(booking.signing_opens_at)}.
						</p>
					{:else if closed(booking)}
						<p class="text-lg font-semibold text-(--warning-text)">
							Please see a staff member to sign {booking.child_first_name} {booking.signed_in_at ? 'out' : 'in'}.
						</p>
					{:else if !booking.signed_in_at}
						<Button
							fullWidth
							textSize="lg"
							isLoading={busyBookingId === booking.booking_id}
							isDisabled={busyBookingId !== null}
							onclick={() => onsign(booking, 'in')}
						>
							Sign in
						</Button>
					{:else if booking.can_collect}
						<Button
							fullWidth
							textSize="lg"
							isLoading={busyBookingId === booking.booking_id}
							isDisabled={busyBookingId !== null}
							onclick={() => onsign(booking, 'out')}
						>
							Sign out
						</Button>
					{:else}
						<p class="text-lg font-semibold text-(--warning-text)">
							Please see a staff member to collect {booking.child_first_name}.
						</p>
					{/if}
				</div>
			</div>
		</Card>
	{:else}
		<p class="text-center text-xl text-(--text-muted)">
			There are no sessions booked for your children today.
		</p>
	{/each}
</div>
