<!--
    Catches any path under a location that no route matches, and sends the
    user somewhere useful (lib/navigation/not-found.ts).
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import { leaveMissingPage } from '$lib/navigation/not-found';

	let { data } = $props();

	onMount(() => {
		void leaveMissingPage(data.locationCode, Boolean(data.session));
	});
</script>
