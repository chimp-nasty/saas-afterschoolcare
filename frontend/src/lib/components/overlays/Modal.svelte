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
		description,
		children,
		actions,
		dismissible = true,
		onclose
	}: {
		title: string;
		// One line under the title saying what this is for (secondary text).
		description?: string;
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
		<div class="flex flex-col gap-1">
			<h2 class="text-lg font-extrabold text-(--text)">
				{title}
			</h2>

			{#if description}
				<p class="text-sm text-(--text-muted)">{description}</p>
			{/if}
		</div>

		{@render children?.()}

		{#if actions}
			<ActionBar>
				{@render actions()}
			</ActionBar>
		{/if}
	</div>
</dialog>

<style>
	/* Fades in, rising slightly, over a backdrop that fades in too (and out
	   again where the browser can animate a dialog closing). */
	dialog {
		opacity: 1;
		transform: none;
		transition:
			opacity 0.25s ease-out,
			transform 0.25s ease-out,
			overlay 0.25s allow-discrete,
			display 0.25s allow-discrete;
	}

	dialog:not([open]) {
		opacity: 0;
		transform: translateY(0.75rem);
	}

	dialog::backdrop {
		background: var(--overlay);
		backdrop-filter: blur(6px);
		opacity: 1;
		transition:
			opacity 0.25s ease-out,
			overlay 0.25s allow-discrete,
			display 0.25s allow-discrete;
	}

	dialog:not([open])::backdrop {
		opacity: 0;
	}

	@starting-style {
		dialog[open] {
			opacity: 0;
			transform: translateY(0.75rem);
		}

		dialog[open]::backdrop {
			opacity: 0;
		}
	}

	@media (prefers-reduced-motion: reduce) {
		dialog,
		dialog::backdrop {
			transition: none;
		}
	}
</style>
