<script lang="ts">
	type Booking = {
		id: string;
		serviceDate: string;
		serviceCode: string;
		serviceLabel: string;
		childId: string;
		childFirstName: string;
	};

	type Day = {
		date: Date;
		dateKey: string;
		dayLabel: string;
		dayNumber: number;
	};

	let {
		bookings
	}: {
		bookings: Booking[];
	} = $props();

	const serviceColors: Record<string, string> = {
		BSC: '#3b82f6',
		ASC: '#22c55e'
	};

	const serviceOrder = [
		'BSC',
		'ASC'
	];

	const today = new Date();

	let weekOffset = $state(0);
	let selectedDayIndex = $state(
		today.getDay() >= 1 && today.getDay() <= 5
			? today.getDay() - 1
			: 0
	);

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
			{ length: 5 },
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
				booking.serviceDate === selectedDay?.dateKey
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

		return `${weekDays[0].dayNumber} ${weekDays[0].date.toLocaleDateString(
			'en-AU',
			{ month: 'short' }
		)} – ${weekDays[4].dayNumber} ${weekDays[4].date.toLocaleDateString(
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
		serviceCode: string
	): boolean {
		return bookings.some(
			(booking) =>
				booking.serviceDate === dateKey &&
				booking.serviceCode === serviceCode
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
		if (selectedDayIndex < 4) {
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
	<div class="mt-4 grid grid-cols-5">
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
					{#each serviceOrder as serviceCode}
						<div class="flex h-3 items-center justify-center">
							{#if hasBooking(day.dateKey, serviceCode)}
								<span
									class="h-2.5 w-2.5 rounded-full"
									style:background-color={serviceColors[serviceCode]}
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
				disabled={selectedDayIndex === 4}
				aria-label="Next day"
			>
				›
			</button>
		</div>

		<div class="mt-4 min-h-28">
			{#each selectedBookings as booking}
				<div class="mb-4 last:mb-0">
					<p class="font-semibold">
						{booking.childFirstName}
					</p>

					<p class="text-sm text-(--text-muted)">
						{booking.serviceLabel}
					</p>
				</div>
			{:else}
				<p class="text-sm text-(--text-muted)">
					No bookings
				</p>
			{/each}
		</div>
	</div>
</div>