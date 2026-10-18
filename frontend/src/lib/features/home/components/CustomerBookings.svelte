<script lang="ts">
	import type { BookingTableResponse } from '$lib/api/schema';

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

	// Pending bookings open their review screen (pay or cancel).
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

	function previousDay() {
		if (selectedDayIndex > 0) {
			selectedDayIndex -= 1;
		}
	}

	function nextDay() {
		if (selectedDayIndex < DAYS_IN_WEEK - 1) {
			selectedDayIndex += 1;
		}
	}

	function selectDay(index: number) {
		selectedDayIndex = index;
	}

	function formatSelectedDate(date: Date): string {
		return date.toLocaleDateString(
			'en-AU',
			{
				weekday: 'long',
				day: 'numeric',
				month: 'long'
			}
		);
	}
</script>

<div class="w-full">
	<!-- Week navigation -->
	<div class="flex items-center justify-between">
		<button
			type="button"
			class="cursor-pointer px-3 py-2 text-lg"
			onclick={previousWeek}
			aria-label="Previous week"
		>
			‹
		</button>

		<p class="text-sm font-semibold">
			{weekLabel}
		</p>

		<button
			type="button"
			class="cursor-pointer px-3 py-2 text-lg"
			onclick={nextWeek}
			aria-label="Next week"
		>
			›
		</button>
	</div>

	<!-- Week -->
	<div class="mt-4 grid grid-cols-7">
		{#each weekDays as day, index}
			<button
				type="button"
				class={[
					'flex cursor-pointer flex-col items-center rounded-md py-2',
					selectedDayIndex === index
						? 'bg-(--surface-muted)'
						: ''
				]}
				onclick={() => selectDay(index)}
			>
				<span
					class="text-xs font-semibold text-(--text-muted)"
				>
					{day.dayLabel}
				</span>

				<span class="mt-1 text-sm">
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
		<div class="flex items-center justify-between">
			<button
				type="button"
				class="cursor-pointer px-3 py-2 text-lg disabled:cursor-default disabled:opacity-25"
				onclick={previousDay}
				disabled={selectedDayIndex === 0}
				aria-label="Previous day"
			>
				‹
			</button>

			<p class="font-semibold">
				{formatSelectedDate(selectedDay.date)}
			</p>

			<button
				type="button"
				class="cursor-pointer px-3 py-2 text-lg disabled:cursor-default disabled:opacity-25"
				onclick={nextDay}
				disabled={selectedDayIndex === DAYS_IN_WEEK - 1}
				aria-label="Next day"
			>
				›
			</button>
		</div>

		<div class="mt-4 min-h-28">
			{#each selectedBookings as booking (booking.id)}
				{#snippet details()}
					<span
						class="mt-1.5 h-2.5 w-2.5 shrink-0 rounded-full"
						style:background-color={serviceColor(booking.service_name)}
					></span>

					<div>
						<p class="font-semibold">
							{booking.child_name}
						</p>

						<p class="text-sm text-(--text-muted)">
							{booking.service_name}
							{#if booking.booking_status === 'PENDING'}
								· <span class="text-(--primary)">Awaiting payment ›</span>
							{/if}
						</p>
					</div>
				{/snippet}

				{#if booking.booking_status === 'PENDING'}
					<a
						href={reviewHref(booking)}
						class="-mx-2 mb-2 flex items-start gap-3 rounded-md px-2 py-2 last:mb-0 hover:bg-(--surface-muted)"
					>
						{@render details()}
					</a>
				{:else}
					<div class="mb-4 flex items-start gap-3 last:mb-0">
						{@render details()}
					</div>
				{/if}
			{:else}
				<p class="text-sm text-(--text-muted)">
					No bookings
				</p>
			{/each}
		</div>
	</div>
</div>
