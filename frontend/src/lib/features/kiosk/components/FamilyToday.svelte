<!--
    Today's sessions for the children a pickup person may collect, one tile
    each: where the child is up to (a badge), and the single next step for
    that session. When the centre only allows signing around each session
    (2 hours either side, "Enforce service times"), the step is a locked
    button saying when it opens, or to see staff once it's closed, instead
    of one that would be refused.
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Pill from '$lib/components/text/Pill.svelte';

	import { Lock } from 'lucide-svelte';

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

<!-- Every tile's action is the same width, whatever it says. -->
{#snippet locked(text: string)}
	<Button fullWidth textSize="lg" isDisabled>
		<Lock size={20} aria-hidden="true" />
		{text}
	</Button>
{/snippet}

<div class="flex flex-col gap-4">
	{#each bookings as booking (booking.booking_id)}
		<Card border>
			<div class="flex items-center justify-between gap-6">
				<div class="flex min-w-0 flex-col gap-2">
					<div class="flex flex-wrap items-center gap-3">
						<p class="text-2xl font-extrabold text-(--text)">
							{booking.child_first_name} {booking.child_last_initial}.
						</p>

						{#if booking.signed_out_at}
							<Pill size="kiosk" tone="success">Signed out {formatClock(booking.signed_out_at)}</Pill>
						{:else if booking.signed_in_at}
							<Pill size="kiosk" tone="success">Signed in {formatClock(booking.signed_in_at)}</Pill>
						{:else}
							<Pill size="kiosk">Not signed in</Pill>
						{/if}
					</div>

					<p class="text-lg text-(--text-muted)">
						{booking.service_name} · {formatTimeRange(booking.start_time, booking.end_time)}
					</p>

					{#if !booking.signed_out_at && closed(booking)}
						<p class="text-lg font-semibold text-(--warning-text)">
							Please see a staff member to sign {booking.child_first_name} {booking.signed_in_at ? 'out' : 'in'}.
						</p>
					{:else if booking.signed_in_at && !booking.signed_out_at && !booking.can_collect}
						<p class="text-lg font-semibold text-(--warning-text)">
							Please see a staff member to collect {booking.child_first_name}.
						</p>
					{/if}
				</div>

				<div class="w-60 shrink-0">
					{#if booking.signed_out_at}
						<!-- Done for today. -->
					{:else if !booking.signed_in_at && notYetOpen(booking) && booking.signing_opens_at}
						{@render locked(`Opens ${formatClock(booking.signing_opens_at)}`)}
					{:else if closed(booking)}
						{@render locked('See staff')}
					{:else if !booking.signed_in_at}
						<Button
							fullWidth
							textSize="lg"
							class="min-h-16"
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
							class="min-h-16"
							isLoading={busyBookingId === booking.booking_id}
							isDisabled={busyBookingId !== null}
							onclick={() => onsign(booking, 'out')}
						>
							Sign out
						</Button>
					{:else}
						{@render locked('See staff')}
					{/if}
				</div>
			</div>
		</Card>
	{:else}
		<EmptyState size="kiosk" message="There are no sessions booked for your children today." />
	{/each}
</div>
