<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';

	let {
		children
	}: {
		children?: () => any;
	} = $props();

	let dialogEl: HTMLDialogElement;

	export function open() {
		dialogEl.showModal();
	}

	export function close() {
		dialogEl.close();
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === dialogEl) {
			close();
		}
	}
</script>

<dialog
	bind:this={dialogEl}
	onclick={handleBackdropClick}
	class="
		fixed
		inset-0
		z-50
		m-auto
		max-h-none
		max-w-none
		border-0
		bg-transparent
		p-0
	"
>
	<Card>
		{#if children}
			{@render children()}
		{/if}
	</Card>
</dialog>

<style>
	dialog::backdrop {
		background: rgba(0, 0, 0, 0.2);
		backdrop-filter: blur(6px);
	}
</style>