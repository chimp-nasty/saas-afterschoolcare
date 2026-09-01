<script lang="ts">
	import { fly } from 'svelte/transition';

	import Card from '$lib/components/layout/Card.svelte';

	import {
		response,
		clearResponse
	} from './state.svelte';
</script>

{#if response.message}
	<button
		type="button"
		class="
			fixed
			top-8
			left-4
			right-4
			z-[100]
			text-left
			rounded-2xl
		"
		onclick={clearResponse}
		transition:fly={{
			y: -12,
			duration: 200
		}}
	>
		<Card border>
			<div
				class={[
					'px-4 py-3 text-sm font-bold rounded-2xl',
					response.ok
						? 'bg-(--success-soft) text-(--success-text)'
						: 'bg-(--danger-soft) text-(--danger-text)'
				]}
			>
				{response.message}
			</div>
		</Card>
	</button>
{/if}