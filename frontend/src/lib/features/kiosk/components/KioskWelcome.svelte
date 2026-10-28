<!--
    The family kiosk's welcome, beside the mobile keypad: what to do, and
    the centre's sessions today with when signing opens and closes for each
    (nothing about families: it's shown before anyone logs in). A message
    from the last person's session (e.g. it timed out) shows here too.
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import Pill from '$lib/components/text/Pill.svelte';

	import type { KioskServiceTodayResponse } from '$lib/api/schema';
	import { formatTimeRange } from '$lib/utils/helpers';
	import { formatClock } from '../kiosk';

	let {
		sessions,
		notice = null
	}: {
		sessions: KioskServiceTodayResponse[];
		notice?: string | null;
	} = $props();

	let now = $state(Date.now());
	let ticker: ReturnType<typeof setInterval> | null = null;

	// Where signing is up to for a session, right now.
	function signingStatus(session: KioskServiceTodayResponse): { tone: 'success' | 'neutral' | 'warning'; label: string; detail: string } {
		const opens = session.signing_opens_at ? Date.parse(session.signing_opens_at) : null;
		const closes = session.signing_closes_at ? Date.parse(session.signing_closes_at) : null;

		if (opens !== null && now < opens) {
			return { tone: 'neutral', label: 'Not open yet', detail: `Signing in opens at ${formatClock(session.signing_opens_at!)}` };
		}

		if (closes !== null && now > closes) {
			return { tone: 'warning', label: 'Closed', detail: 'See a staff member' };
		}

		return {
			tone: 'success',
			label: 'Open',
			detail: closes !== null ? `Signing open until ${formatClock(session.signing_closes_at!)}` : 'Signing open today'
		};
	}

	onMount(() => {
		ticker = setInterval(() => (now = Date.now()), 15_000);
	});

	onDestroy(() => {
		if (ticker) clearInterval(ticker);
	});
</script>

<div class="flex flex-col gap-6">
	<div class="flex flex-col gap-3">
		<span class="h-1 w-12 rounded-full bg-(--accent)" aria-hidden="true"></span>
		<h1 class="text-4xl font-extrabold text-(--text)">Welcome</h1>
		<p class="text-xl text-(--text-muted)">
			Sign your children in or out with your mobile number and kiosk PIN.
		</p>
	</div>

	{#if notice}
		<Notice size="kiosk">{notice}</Notice>
	{/if}

	<section class="flex flex-col gap-3">
		<p class="label-text">Today</p>

		{#each sessions as session (session.service_name)}
			{@const status = signingStatus(session)}
			<Card border>
				<div class="flex items-center justify-between gap-4">
					<div class="flex min-w-0 flex-col gap-1">
						<p class="text-xl font-extrabold text-(--text)">{session.service_name}</p>
						<p class="text-lg text-(--text-muted)">
							{formatTimeRange(session.start_time, session.end_time)} · {status.detail}
						</p>
					</div>

					<Pill size="kiosk" tone={status.tone}>{status.label}</Pill>
				</div>
			</Card>
		{:else}
			<EmptyState size="kiosk" message="No sessions are running today." />
		{/each}
	</section>
</div>
