<!--
    A family's payments in Admin › Families, newest first: each checkout's
    amount and Stripe status, how many bookings it paid for, what's been
    refunded from it, and its receipt, for reconciling with Stripe.
-->
<script lang="ts">
	import GridTable from '$lib/components/layout/GridTable.svelte';

	import type { FamilyPaymentResponse } from '$lib/api/schema';
	import { formatMoney, formatTimestamp } from '$lib/utils/helpers';

	let {
		payments
	}: {
		payments: FamilyPaymentResponse[];
	} = $props();

	const STATUS: Record<string, string> = {
		PENDING: 'Awaiting payment',
		SUCCEEDED: 'Paid',
		FAILED: 'Failed'
	};

	const columns = 'minmax(9rem,1.2fr) 7rem minmax(8rem,1fr) 6rem 7rem 6rem';
</script>

<GridTable
	items={payments}
	key={(payment) => payment.id}
	{columns}
	headers={['Date', 'Amount', 'Status', 'Bookings', 'Refunded', 'Receipt']}
	label="Payments"
	minWidth="46rem"
	maxRows={12}
	empty="No payments yet."
>
	{#snippet row(payment)}
		<span class="text-base font-semibold text-(--text)" role="cell">{formatTimestamp(payment.paid_at ?? payment.created_at)}</span>
		<span class="text-base text-(--text)" role="cell">{formatMoney(payment.total_cents, payment.currency)}</span>
		<span class="text-base text-(--text)" role="cell">{STATUS[payment.stripe_status] ?? payment.stripe_status}</span>
		<span class="text-base text-(--text)" role="cell">{payment.bookings}</span>
		<span class="text-base text-(--text)" role="cell">
			{payment.refunded_cents ? formatMoney(payment.refunded_cents, payment.currency) : '—'}
		</span>
		<span class="text-base" role="cell">
			{#if payment.receipt_url}
				<a class="text-(--hyperlink) underline" href={payment.receipt_url} target="_blank" rel="noopener noreferrer">Receipt</a>
			{:else}
				—
			{/if}
		</span>
	{/snippet}
</GridTable>
