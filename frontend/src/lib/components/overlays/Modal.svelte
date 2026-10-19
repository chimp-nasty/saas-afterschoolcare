<!--
    A modal dialog. A bottom sheet on mobile (easy to reach with a thumb), a
    centred card from md. Open and close it through bind:this:

        <Modal bind:this={modal} title="Cancel booking?">...</Modal>
        modal.open()

    Put its buttons in an ActionBar inside `actions`. Escape and tapping the
    backdrop close it.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';

	let {
		title,
		children,
		actions,
		onclose
	}: {
		title: string;
		children?: Snippet;
		actions?: Snippet;
		// However it closed: a button, Escape or the backdrop.
		onclose?: () => void;
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
	{onclose}
	aria-label={title}
	class="
		fixed inset-x-0 bottom-0 z-50 mx-0 mt-auto mb-0 w-full max-w-none
		rounded-t-2xl border border-(--border) bg-(--surface) p-5
		pb-[calc(1.25rem+env(safe-area-inset-bottom))] text-(--text)
		md:m-auto md:max-w-md md:rounded-2xl md:pb-5
	"
>
	<div class="flex flex-col gap-4">
		<h2 class="text-lg font-extrabold text-(--text)">
			{title}
		</h2>

		{@render children?.()}

		{#if actions}
			<ActionBar>
				{@render actions()}
			</ActionBar>
		{/if}
	</div>
</dialog>

<style>
	dialog::backdrop {
		background: var(--overlay);
		backdrop-filter: blur(6px);
	}
</style>
