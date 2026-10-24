<!--
    The business's Stripe account at a glance: how it stands and its flags.
    Shown read-only on a centre's Admin › Payments and above the owner's
    controls in Business settings › Payments.
-->
<script lang="ts">
	import LabelValueList from '$lib/components/text/LabelValueList.svelte';
	import Notice from '$lib/components/text/Notice.svelte';

	import type { StripeAccountStatusResponse } from '$lib/api/schema';
	import { stripeStanding } from '$lib/features/payments/stripeStanding';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		account
	}: {
		account: StripeAccountStatusResponse | null;
	} = $props();

	const standing = $derived(stripeStanding(account));

	const onOff = (value: boolean | undefined) => (value ? 'On' : 'Off');
</script>

<Notice tone={standing.tone}>{standing.text}</Notice>

{#if account?.connected}
	<LabelValueList
		columns={3}
		items={[
			{ label: 'Setup', value: account.details_submitted ? 'Finished' : 'Not finished' },
			{ label: 'Card payments', value: onOff(account.charges_enabled) },
			{ label: 'Payouts', value: onOff(account.payouts_enabled) },
			{ label: 'Online payments', value: account.disconnected ? 'Turned off' : 'Turned on' },
			{ label: 'Connected', value: account.connected_at ? formatTimestamp(account.connected_at) : null },
			{ label: 'Stripe account', value: account.stripe_account_id }
		]}
	/>
{/if}
