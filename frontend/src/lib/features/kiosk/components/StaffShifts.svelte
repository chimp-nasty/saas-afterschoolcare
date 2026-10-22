<!--
    The staff kiosk's Shifts tab, laid out like a time clock: the time now
    and one Clock in / out button (choosing your name and entering your PIN
    happen in the kiosk's task window), then who's on shift and who has
    clocked out today. Only people on shift can act at the kiosk. Who is
    rostered on isn't known here (rosters come later).
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { StaffKioskMemberResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';
	import { formatClock, type ClockedOut } from '../kiosk';

	let {
		members,
		clockedOut,
		onclock
	}: {
		members: StaffKioskMemberResponse[];
		// Today's clock-outs at this tablet.
		clockedOut: ClockedOut[];
		onclock: () => void;
	} = $props();

	let now = $state(new Date().toISOString());
	let ticker: ReturnType<typeof setInterval> | null = null;

	const onShift = $derived(members.filter((m) => m.on_shift));
	const unclosed = $derived(members.filter((m) => m.unclosed_shift_started_at));

	// Whole hours and minutes since a time ("2h 15m").
	function since(value: string): string {
		const minutes = Math.max(0, Math.floor((Date.parse(now) - Date.parse(value)) / 60_000));

		return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
	}

	onMount(() => {
		ticker = setInterval(() => (now = new Date().toISOString()), 15_000);
	});

	onDestroy(() => {
		if (ticker) clearInterval(ticker);
	});
</script>

<div class="flex flex-col gap-6">
	<Card border>
		<div class="flex flex-col items-center gap-4 py-4 text-center">
			<p class="text-5xl font-extrabold text-(--text)">{formatClock(now)}</p>
			<p class="text-lg text-(--text-muted)">{formatTimestamp(now)}</p>

			<div class="w-full max-w-xs">
				<Button fullWidth onclick={onclock}>Clock in / out</Button>
			</div>
		</div>
	</Card>

	<section class="flex flex-col gap-3">
		<SectionHeading size="kiosk" title={`On shift (${onShift.length})`} />

		<Card border padded={false}>
			<ul class="flex flex-col">
				{#each onShift as member (member.user_id)}
					<li class="flex min-h-12 items-center justify-between gap-4 border-b border-(--border) px-5 py-2 last:border-b-0">
						<span class="flex items-center gap-2">
							<span class="size-2.5 rounded-full bg-(--success-text)" aria-hidden="true"></span>
							<span class="text-base font-semibold text-(--text)">{member.first_name} {member.last_name}</span>
						</span>
						{#if member.shift_started_at}
							<span class="text-sm text-(--text-muted)">
								In {formatClock(member.shift_started_at)} · {since(member.shift_started_at)}
							</span>
						{/if}
					</li>
				{:else}
					<li class="px-5"><EmptyState size="kiosk" message="Nobody is clocked in." /></li>
				{/each}
			</ul>
		</Card>
	</section>

	<section class="flex flex-col gap-3">
		<SectionHeading size="kiosk" title={`Clocked out today (${clockedOut.length})`} />

		<Card border padded={false}>
			<ul class="flex flex-col">
				{#each clockedOut as shift (`${shift.userId}:${shift.endedAt}`)}
					<li class="flex min-h-12 items-center justify-between gap-4 border-b border-(--border) px-5 py-2 last:border-b-0">
						<span class="flex items-center gap-2">
							<span class="size-2.5 rounded-full bg-(--text-muted)" aria-hidden="true"></span>
							<span class="text-base font-semibold text-(--text)">{shift.name}</span>
						</span>
						<span class="text-sm text-(--text-muted)">
							{#if shift.startedAt}In {formatClock(shift.startedAt)} · {/if}Out {formatClock(shift.endedAt)}
						</span>
					</li>
				{:else}
					<li class="px-5"><EmptyState size="kiosk" message="Nobody has clocked out yet." /></li>
				{/each}
			</ul>
		</Card>
	</section>

	{#if unclosed.length}
		<section class="flex flex-col gap-3">
			<SectionHeading size="kiosk" title="Didn't clock out" />

			<Card border padded={false}>
				<ul class="flex flex-col">
					{#each unclosed as member (member.user_id)}
						<li class="flex min-h-12 items-center justify-between gap-4 border-b border-(--border) px-5 py-2 last:border-b-0">
							<span class="text-base font-semibold text-(--warning-text)">⚠ {member.first_name} {member.last_name}</span>
							{#if member.unclosed_shift_started_at}
								<span class="text-sm text-(--text-muted)">From {formatTimestamp(member.unclosed_shift_started_at)}; asked when they next clock in</span>
							{/if}
						</li>
					{/each}
				</ul>
			</Card>
		</section>
	{/if}
</div>
