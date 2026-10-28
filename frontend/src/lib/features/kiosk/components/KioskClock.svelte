<!--
    Today's date and the time, live, for the kiosk's header ("Tue 28 Oct ·
    3:12pm"). The tablet is at the centre, so its own clock and timezone
    are the centre's.
-->
<script lang="ts">
	import { onDestroy, onMount } from 'svelte';

	import { formatClock } from '../kiosk';

	let now = $state(new Date());
	let ticker: ReturnType<typeof setInterval> | null = null;

	const date = $derived(
		now.toLocaleDateString('en-AU', { weekday: 'short', day: 'numeric', month: 'short' }).replace(',', '')
	);

	onMount(() => {
		ticker = setInterval(() => (now = new Date()), 10_000);
	});

	onDestroy(() => {
		if (ticker) clearInterval(ticker);
	});
</script>

<p class="text-right">
	<span class="block text-3xl font-extrabold text-(--text) tabular-nums">{formatClock(now.toISOString())}</span>
	<span class="label-text">{date}</span>
</p>
