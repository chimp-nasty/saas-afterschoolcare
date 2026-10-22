<script lang="ts">
	import { ChevronLeft, ChevronRight } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Pill from '$lib/components/text/Pill.svelte';

	import type { BookingTableResponse } from '$lib/api/schema';
	import { BOOKING_STATUS_LABELS } from '$lib/features/bookings/status';
	import { formatDate, formatTimeRange } from '$lib/utils/helpers';

	type Day = {
		date: Date;
		dateKey: string;
		dayLabel: string;
		dayNumber: number;
	};

	let {
		bookings,
		locationCode
	}: {
		bookings: BookingTableResponse[];
		locationCode: string;
	} = $props();

	// Every booking opens its group's review screen: pay or cancel a pending
	// one, see or refund a confirmed one.
	function reviewHref(booking: BookingTableResponse): string {
		return `/${locationCode}/bookings/${booking.booking_group_id}/review`;
	}

	const DAYS_IN_WEEK = 7;

	// One dot row per service the customer has booked, in a stable order,
	// each with its own colour (cycled if there are more services).
	const SERVICE_PALETTE = [
		'var(--primary)',
		'var(--secondary-strong)',
		'var(--success)',
		'var(--text-muted)'
	];

	const services = $derived(
		[...new Set(bookings.map((booking) => booking.service_name))].sort()
	);

	function serviceColor(serviceName: string): string {
		const index = services.indexOf(serviceName);

		return SERVICE_PALETTE[index % SERVICE_PALETTE.length];
	}

	const today = new Date();

	let weekOffset = $state(0);

	// Monday = 0 ... Sunday = 6
	let selectedDayIndex = $state((today.getDay() + 6) % 7);

	const weekDays = $derived.by(() => {
		const current = new Date(today);

		const day = current.getDay();
		const distanceToMonday =
			day === 0
				? -6
				: 1 - day;

		current.setDate(
			current.getDate() +
			distanceToMonday +
			weekOffset * 7
		);

		return Array.from(
			{ length: DAYS_IN_WEEK },
			(_, index): Day => {
				const date = new Date(current);
				date.setDate(current.getDate() + index);

				return {
					date,
					dateKey: formatDateKey(date),
					dayLabel: date
						.toLocaleDateString('en-AU', {
							weekday: 'short'
						})
						.toUpperCase(),
					dayNumber: date.getDate()
				};
			}
		);
	});

	const selectedDay = $derived(
		weekDays[selectedDayIndex]
	);

	const selectedBookings = $derived(
		bookings.filter(
			(booking) =>
				booking.service_date === selectedDay?.dateKey
		)
	);

	const weekLabel = $derived.by(() => {
		if (weekOffset === 0) {
			return 'This week';
		}

		if (weekOffset === 1) {
			return 'Next week';
		}

		if (weekOffset === -1) {
			return 'Last week';
		}

		const first = weekDays[0];
		const last = weekDays[DAYS_IN_WEEK - 1];

		return `${first.dayNumber} ${first.date.toLocaleDateString(
			'en-AU',
			{ month: 'short' }
		)} – ${last.dayNumber} ${last.date.toLocaleDateString(
			'en-AU',
			{ month: 'short' }
		)}`;
	});

	function formatDateKey(date: Date): string {
		const year = date.getFullYear();
		const month = String(date.getMonth() + 1).padStart(2, '0');
		const day = String(date.getDate()).padStart(2, '0');

		return `${year}-${month}-${day}`;
	}

	function hasBooking(
		dateKey: string,
		serviceName: string
	): boolean {
		return bookings.some(
			(booking) =>
				booking.service_date === dateKey &&
				booking.service_name === serviceName
		);
	}

	function previousWeek() {
		weekOffset -= 1;
		selectedDayIndex = 0;
	}

	function nextWeek() {
		weekOffset += 1;
		selectedDayIndex = 0;
	}

	function selectDay(index: number) {
		selectedDayIndex = index;
	}

</script>

<div class="w-full">
	<!-- Week navigation -->
	<div class="flex items-center justify-between">
		<Button
			variant="ghost"
			onclick={previousWeek}
			aria-label="Previous week"
		>
			<ChevronLeft size={20} />
		</Button>

		<p class="label-text">
			{weekLabel}
		</p>

		<Button
			variant="ghost"
			onclick={nextWeek}
			aria-label="Next week"
		>
			<ChevronRight size={20} />
		</Button>
	</div>

	<!-- Week -->
	<div class="mt-4 grid grid-cols-7">
		{#each weekDays as day, index}
			<button
				type="button"
				class={[
					'flex cursor-pointer flex-col items-center rounded-lg py-2',
					selectedDayIndex === index
						? 'bg-(--primary-soft) text-(--primary)'
						: ''
				]}
				onclick={() => selectDay(index)}
			>
				<span
					class="label-text"
				>
					{day.dayLabel}
				</span>

				<span class="mt-1 text-sm font-semibold">
					{day.dayNumber}
				</span>

				<div class="mt-3 flex min-h-8 flex-col gap-1.5">
					{#each services as serviceName}
						<div class="flex h-3 items-center justify-center">
							{#if hasBooking(day.dateKey, serviceName)}
								<span
									class="h-2.5 w-2.5 rounded-full"
									style:background-color={serviceColor(serviceName)}
								></span>
							{/if}
						</div>
					{/each}
				</div>
			</button>
		{/each}
	</div>

	<div class="my-4 border-t border-(--border)"></div>

	<!-- Selected day -->
	<div>
		<p class="text-center text-lg font-extrabold text-(--text)">
			{formatDate(selectedDay.dateKey)}
		</p>

		<div class="mt-4 flex min-h-28 flex-col gap-2">
			{#each selectedBookings as booking (booking.id)}
				<a
					href={reviewHref(booking)}
					class="flex min-h-11 items-center gap-3 rounded-lg border border-(--border) bg-(--surface) px-4 py-3 transition hover:border-(--primary)"
				>
					<span
						class="h-2.5 w-2.5 shrink-0 rounded-full"
						style:background-color={serviceColor(booking.service_name)}
					></span>

					<div class="min-w-0 flex-1">
						<p class="text-base font-semibold text-(--text)">
							{booking.child_name}
						</p>

						<p class="text-sm text-(--text-muted)">
							{booking.service_name} · {formatTimeRange(booking.start_time, booking.end_time)}
							{#if booking.booking_status === 'PENDING'}
								· <Pill tone="warning">{BOOKING_STATUS_LABELS.PENDING}</Pill>
							{/if}
						</p>
					</div>

					<ChevronRight size={18} class="shrink-0 text-(--text-muted)" />
				</a>
			{:else}
				<EmptyState message="No bookings on this day." />
			{/each}
		</div>
	</div>
</div>
