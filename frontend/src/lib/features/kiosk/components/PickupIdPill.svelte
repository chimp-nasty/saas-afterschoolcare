<!--
    A pickup person's photo ID status, the same on the staff kiosk and the
    admin run sheet: sighted (with the date), not sighted (approved without
    ID), or not approved yet.
-->
<script lang="ts">
	import type { RollPickupPersonResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';
	import { PICKUP_ID_STATUS_LABELS, pickupIdStatus } from '../roll';

	let {
		person
	}: {
		person: Pick<RollPickupPersonResponse, 'identity_verified_at' | 'staff_approved_at'>;
	} = $props();

	const status = $derived(pickupIdStatus(person));
</script>

<span
	class={[
		'w-fit rounded-full px-3 py-1 text-sm font-extrabold',
		status === 'sighted' && 'bg-(--success-soft) text-(--success-text)',
		status === 'not_sighted' && 'bg-(--warning-soft) text-(--warning-text)',
		status === 'not_approved' && 'bg-(--surface-muted) text-(--text-muted)'
	]}
>
	{#if status === 'sighted'}✓{:else if status === 'not_sighted'}⚠{/if}
	{PICKUP_ID_STATUS_LABELS[status]}{#if status === 'sighted' && person.identity_verified_at}&nbsp;{formatTimestamp(person.identity_verified_at)}{/if}
</span>
