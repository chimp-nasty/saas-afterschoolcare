<!--
    A modal dialog for small forms or extra content. A bottom sheet on mobile
    (easy to reach with a thumb), a centred card from md. Open and close it
    through bind:this:

        <Modal bind:this={modal} title="Add a note">...</Modal>
        modal.open()

    Put its buttons in an ActionBar inside `actions`. Escape and tapping the
    backdrop close it (unless `dismissible` is false).

    For a yes/no confirmation use confirmAction() instead (ConfirmDialog).
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import ActionBar from '$lib/components/actions/ActionBar.svelte';

	let {
		title,
		children,
		actions,
		dismissible = true,
		onclose
	}: {
		title: string;
		children?: Snippet;
		actions?: Snippet;
		// False while something is running: Escape and the backdrop do nothing.
		dismissible?: boolean;
		// However it closed: a button, Escape or the backdrop.
		onclose?: () => void;
	} = $props();

	let dialogEl: HTMLDialogElement;

	export function open() {
		if (!dialogEl.open) {
			dialogEl.showModal();
		}
	}

	export function close() {
		dialogEl.close();
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === dialogEl && dismissible) {
			close();
		}
	}

	// Escape fires "cancel" before closing; stop it while not dismissible.
	function handleCancel(event: Event) {
		if (!dismissible) {
			event.preventDefault();
		}
	}
</script>

<dialog
	bind:this={dialogEl}
	onclick={handleBackdropClick}
	oncancel={handleCancel}
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
