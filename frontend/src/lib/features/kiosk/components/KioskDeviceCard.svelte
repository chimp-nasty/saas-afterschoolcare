<!--
    One of the location's two kiosk tablets in Admin › Kiosks: whether it's
    added and paired, when it was last used, and the admin's actions. The
    two cards sit side by side, so the actions are a fixed two-column row at
    the bottom of the card, the main action always on the right: the
    buttons line up across both cards whatever the text above them.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';

	import type { KioskDeviceResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';
	import { formatClock } from '../kiosk';
	import { KIOSK_KINDS, type KioskKind } from '../devices';

	let {
		kind,
		device,
		busy,
		onadd,
		onnewcode,
		onrevoke
	}: {
		kind: KioskKind;
		// The active kiosk of this kind, if there is one.
		device: KioskDeviceResponse | null;
		busy: boolean;
		onadd: () => void;
		onnewcode: (device: KioskDeviceResponse) => void;
		onrevoke: (device: KioskDeviceResponse) => void;
	} = $props();

	const info = $derived(KIOSK_KINDS[kind]);

	const status = $derived.by(() => {
		if (!device) return 'Not added';
		if (device.paired_at) {
			return device.last_used
				? `Paired · last used ${formatTimestamp(device.last_used)} ${formatClock(device.last_used)}`
				: 'Paired';
		}

		return 'Waiting to be paired with its setup code';
	});
</script>

<Card border>
	<!-- Fills the card, which the page's grid stretches to the taller one. -->
	<div class="flex h-full flex-col gap-4">
		<div class="flex flex-col gap-1">
			<p class="label-text">{info.label}</p>
			<p class="text-lg font-extrabold text-(--text)">{device?.name ?? '—'}</p>
			<p class="text-sm text-(--text-muted)">{status}</p>
			<p class="text-sm text-(--text-muted)">{info.description}</p>
		</div>

		<div class="mt-auto grid grid-cols-2 gap-3">
			{#if device}
				<Button variant="ghost" fullWidth isDisabled={busy} onclick={() => onrevoke(device)}>Revoke</Button>
				<Button fullWidth isDisabled={busy} onclick={() => onnewcode(device)}>New setup code</Button>
			{:else}
				<span></span>
				<Button fullWidth isDisabled={busy} onclick={onadd}>Add kiosk</Button>
			{/if}
		</div>
	</div>
</Card>
