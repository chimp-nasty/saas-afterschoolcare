<!--
    The family's bell in the header: their actions page, with how many they
    haven't seen yet. Actions are messages to families, so only customers
    get it.
-->
<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { Bell } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';

	const count = $derived(page.data.uncitedActionCount ?? 0);
</script>

<Button
	variant="ghost"
	class="group relative"
	aria-label="Notifications"
	onclick={() => goto(`/${page.params.location_code}/actions`)}
>
	<!-- Unseen messages: it rings now and then (not with reduced motion). -->
	<span
		class={[
			'inline-flex origin-top group-hover:animate-[bell-ring_0.5s_ease-in-out]',
			count > 0 && 'motion-safe:animate-[bell-nudge_30s_ease-in-out_1s_infinite]'
		]}
	>
		<Bell size={20} />
	</span>

	{#if count > 0}
		<span
			class="absolute right-0.5 bottom-0.5 flex min-h-4 min-w-4 items-center justify-center rounded-full bg-(--danger) px-1 text-[10px] leading-none font-extrabold text-white"
		>
			{count > 99 ? '99+' : count}
		</span>
	{/if}
</Button>
