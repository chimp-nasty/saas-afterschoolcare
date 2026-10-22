<!--
    A pickup person's photo ID status, the same on the staff kiosk and the
    admin website: sighted (with the date), not sighted (approved without
    ID), or not approved yet. The kiosk passes size="kiosk".
-->
<script lang="ts">
	import Pill from '$lib/components/text/Pill.svelte';

	import type { RollPickupPersonResponse } from '$lib/api/schema';
	import type { TextSize, Tone } from '$lib/components/text/textSize';
	import { formatTimestamp } from '$lib/utils/helpers';
	import { PICKUP_ID_STATUS_LABELS, pickupIdStatus, type PickupIdStatus } from '../roll';

	let {
		person,
		size = 'web'
	}: {
		person: Pick<RollPickupPersonResponse, 'identity_verified_at' | 'staff_approved_at'>;
		size?: TextSize;
	} = $props();

	const TONES: Record<PickupIdStatus, Tone> = {
		sighted: 'success',
		not_sighted: 'warning',
		not_approved: 'neutral'
	};

	const status = $derived(pickupIdStatus(person));
</script>

<Pill tone={TONES[status]} {size}>
	{#if status === 'sighted'}✓{:else if status === 'not_sighted'}⚠{/if}
	{PICKUP_ID_STATUS_LABELS[status]}{#if status === 'sighted' && person.identity_verified_at}&nbsp;{formatTimestamp(person.identity_verified_at)}{/if}
</Pill>
