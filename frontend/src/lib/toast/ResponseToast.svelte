<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';

	import { response } from './state.svelte';
</script>

{#if response.message}
	<Card border>
		<div
			class={[
				'px-4 py-3 text-sm font-bold',
				response.ok
					? 'bg-(--success-soft) text-(--success-text)'
					: 'bg-(--danger-soft) text-(--danger-text)'
			]}
		>
			{response.message}
		</div>
	</Card>
{/if}