<!--
    The one confirmation dialog, driven by confirmAction(). Mounted once in
    the tenant layout. While a confirmed action runs it can't be dismissed.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Modal from './Modal.svelte';

	import { confirmState } from './confirm.svelte';

	let modal: Modal;
	let isBusy = $state(false);

	const request = $derived(confirmState.current);

	const cancelLabel = $derived(
		request?.cancelLabel ?? (request?.tone === 'danger' ? 'Keep' : 'Cancel')
	);

	$effect(() => {
		if (request) {
			modal.open();
		}
	});

	function finish(confirmed: boolean) {
		const current = confirmState.current;

		confirmState.current = null;
		modal.close();
		current?.resolve(confirmed);
	}

	async function confirm() {
		const current = confirmState.current;

		if (!current) {
			return;
		}

		if (current.action) {
			isBusy = true;

			try {
				await current.action();
			} finally {
				isBusy = false;
			}
		}

		finish(true);
	}
</script>

<Modal
	bind:this={modal}
	title={request?.title ?? ''}
	dismissible={!isBusy}
	onclose={() => confirmState.current && finish(false)}
>
	<!-- What happens: body text, it's the point of the dialog. -->
	<p class="text-base text-(--text)">
		{request?.message}
	</p>

	{#snippet actions()}
		<Button variant="ghost" onclick={() => finish(false)} isDisabled={isBusy}>
			{cancelLabel}
		</Button>

		<Button
			variant={request?.tone === 'danger' ? 'danger' : 'default'}
			onclick={confirm}
			isLoading={isBusy}
		>
			{request?.confirmLabel}
		</Button>
	{/snippet}
</Modal>
