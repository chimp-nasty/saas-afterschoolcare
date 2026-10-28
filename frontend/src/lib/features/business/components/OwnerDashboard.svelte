<!--
    The owner's dashboard (docs/owner-dashboard.md): a week's numbers (or
    all time) beside the week before, what needs attention now, payments to
    refund in Stripe, and who the families are. Every centre, or one. Prev
    and Next step a week at a time, as far as you like; This week comes
    back. The page owns the week and centre (they're in the address); this
    shows them and asks to change them.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import Select from '$lib/components/forms/fields/Select.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { BusinessLocationResponse, OwnerDashboardResponse } from '$lib/api/schema';
	import { formatDate, formatMoney, formatTimestamp } from '$lib/utils/helpers';

	let {
		dashboard,
		locations,
		week,
		locationId,
		onchange
	}: {
		dashboard: OwnerDashboardResponse;
		locations: BusinessLocationResponse[];
		// Weeks from this one (-1 last week); null for all time.
		week: number | null;
		locationId: string | null;
		onchange: (week: number | null, locationId: string | null) => void;
	} = $props();

	// The same width for every period button, whatever it says.
	const PERIOD_BUTTON = 'w-full md:w-32';

	const current = $derived(dashboard.current);
	const previous = $derived(dashboard.previous);
	const attention = $derived(dashboard.attention);
	const currency = $derived(current.currency ?? previous?.currency ?? 'AUD');

	const periodLabel = $derived(
		dashboard.from_date && dashboard.to_date
			? `Viewing ${formatDate(dashboard.from_date)} to ${formatDate(dashboard.to_date)}`
			: 'Viewing all time'
	);

	// "▲ 12% on last week": null when there's nothing to compare with.
	function change(now: number | null, before: number | null | undefined): { text: string; up: boolean } | null {
		if (now === null || before === null || before === undefined || !previous) return null;
		if (before === 0) return now === 0 ? { text: 'No change', up: true } : { text: 'New this week', up: true };

		const percent = Math.round(((now - before) / before) * 100);

		return { text: `${percent >= 0 ? '▲' : '▼'} ${Math.abs(percent)}%`, up: percent >= 0 };
	}

	type Stat = { label: string; value: string; detail?: string; delta: { text: string; up: boolean } | null };

	function money(cents: number | null): string {
		return cents === null ? '—' : formatMoney(cents, currency);
	}

	function count(value: number | null): string {
		return value === null ? '—' : String(value);
	}

	const headline = $derived<Stat[]>([
		{ label: 'Revenue', value: money(current.revenue_cents), detail: 'Paid sessions in the period, after refunds', delta: change(current.revenue_cents, previous?.revenue_cents) },
		{ label: 'Bookings', value: count(current.bookings), detail: 'Sessions taking place', delta: change(current.bookings, previous?.bookings) },
		{ label: 'Active families', value: count(current.active_families), detail: 'With at least one session', delta: change(current.active_families, previous?.active_families) },
		{ label: 'Registrations', value: count(current.registrations), detail: 'New family accounts', delta: change(current.registrations, previous?.registrations) },
		{
			label: 'Refunds',
			value: count(current.refunds),
			detail: current.refunded_cents === null ? 'Not yet' : `${money(current.refunded_cents)} refunded`,
			delta: null
		}
	]);

	const insights = $derived<Stat[]>([
		{ label: 'Returning families', value: count(current.returning_families), detail: week === null ? 'Booked more than once' : 'Active, and booked before', delta: null },
		{ label: 'Inactive 30 days', value: count(attention.inactive_families), detail: 'Families with no session in the last 30 days', delta: null },
		{ label: 'Average sessions per family', value: current.average_sessions === null ? '—' : String(current.average_sessions), detail: 'Bookings ÷ active families', delta: null }
	]);

	const followUps = $derived([
		{ label: 'New enquiries', value: attention.enquiries_new, detail: 'From the contact form, not replied to' },
		{ label: 'Reactivation requests', value: attention.reactivation_requests, detail: 'Deactivated families asking to come back' },
		{ label: 'Documents requested', value: attention.documents_requested, detail: "Families asked for medical documents who haven't sent them" },
		{ label: 'Payments needing a refund', value: attention.unrefunded_payments.length, detail: 'Paid after their places were released' }
	]);

	const centreOptions = $derived([
		{ value: '', label: 'All centres' },
		...locations.map((location) => ({ value: location.id, label: location.name }))
	]);
</script>

{#snippet statCard(stat: Stat)}
	<Card border>
		<div class="flex flex-col gap-1">
			<p class="label-text">{stat.label}</p>
			<p class="text-2xl font-extrabold text-(--text)">{stat.value}</p>
			{#if stat.delta}
				<p class={['text-sm font-semibold', stat.delta.up ? 'text-(--success-text)' : 'text-(--danger-text)']}>
					{stat.delta.text} <span class="font-normal text-(--text-muted)">on the week before</span>
				</p>
			{/if}
			{#if stat.detail}
				<p class="text-sm text-(--text-muted)">{stat.detail}</p>
			{/if}
		</div>
	</Card>
{/snippet}

<section class="flex flex-col gap-6">
	<div class="flex flex-col gap-4">
		<SectionHeading title="Dashboard" />

		<div class="md:w-64">
			<Select
				aria-label="Centre"
				value={locationId ?? ''}
				options={centreOptions}
				onchange={(value) => onchange(week, value || null)}
			/>
		</div>

		<!-- A week at a time either way, back to this week, or all time
		     (on the right). -->
		<div class="flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
			<div class="grid grid-cols-3 gap-2 md:flex" role="group" aria-label="Week">
				<Button variant="ghost" width={PERIOD_BUTTON} onclick={() => onchange((week ?? 0) - 1, locationId)}>Prev</Button>
				<Button variant={week === 0 ? 'default' : 'ghost'} width={PERIOD_BUTTON} onclick={() => onchange(0, locationId)}>This week</Button>
				<Button variant="ghost" width={PERIOD_BUTTON} onclick={() => onchange((week ?? 0) + 1, locationId)}>Next</Button>
			</div>

			<Button variant={week === null ? 'default' : 'ghost'} width={PERIOD_BUTTON} onclick={() => onchange(null, locationId)}>All time</Button>
		</div>

		<p class="text-sm text-(--text-muted)">{periodLabel}</p>
	</div>

	<div class="grid grid-cols-1 gap-4 md:grid-cols-3 xl:grid-cols-5">
		{#each headline as stat (stat.label)}
			{@render statCard(stat)}
		{/each}
	</div>

	<div class="grid grid-cols-1 gap-6 lg:grid-cols-2">
		<Card border>
			<div class="flex flex-col gap-4">
				<SectionHeading title="Needs attention" description="As things stand now." />

				<ul class="flex flex-col divide-y divide-(--border)">
					<li class="flex items-center justify-between gap-4 py-3">
						<span class="flex flex-col">
							<span class="text-base font-semibold text-(--text)">Medical reviews</span>
							<span class="text-sm text-(--text-muted)">Children waiting for a review</span>
						</span>
						<span class="text-2xl font-extrabold text-(--text)">{attention.reviews_pending}</span>
					</li>

					{#each followUps as item (item.label)}
						<li class="flex items-center justify-between gap-4 py-3">
							<span class="flex flex-col">
								<span class="text-base font-semibold text-(--text)">{item.label}</span>
								<span class="text-sm text-(--text-muted)">{item.detail}</span>
							</span>
							<span class={['text-2xl font-extrabold', item.value ? 'text-(--warning-text)' : 'text-(--text)']}>{item.value}</span>
						</li>
					{/each}

					<li class="flex items-center justify-between gap-4 py-3">
						<span class="flex flex-col">
							<span class="text-base font-semibold text-(--text)">Cancelled without a refund</span>
							<span class="text-sm text-(--text-muted)">In the period, in case of a goodwill refund</span>
						</span>
						<span class="text-2xl font-extrabold text-(--text)">{count(current.cancelled_unrefunded)}</span>
					</li>
				</ul>
			</div>
		</Card>

		<Card border>
			<div class="flex flex-col gap-4">
				<SectionHeading title="Your families" />

				<div class="grid grid-cols-1 gap-4 md:grid-cols-3 lg:grid-cols-1 xl:grid-cols-3">
					{#each insights as stat (stat.label)}
						<div class="flex flex-col gap-1">
							<p class="label-text">{stat.label}</p>
							<p class="text-2xl font-extrabold text-(--text)">{stat.value}</p>
							<p class="text-sm text-(--text-muted)">{stat.detail}</p>
						</div>
					{/each}
				</div>
			</div>
		</Card>
	</div>

	{#if attention.unrefunded_payments.length > 0}
		<Card border>
			<div class="flex flex-col gap-4">
				<SectionHeading
					title="Payments needing a refund"
					description="Paid after their places were released, so nothing was booked. Refund each in your Stripe dashboard: search for its reference."
				/>

				<Notice tone="warning">These can't be refunded from here: nothing in the app is paid.</Notice>

				<GridTable
					items={attention.unrefunded_payments}
					key={(payment) => payment.reference}
					columns="8rem minmax(10rem,1fr) 8rem minmax(10rem,1fr)"
					headers={['Reference', 'Centre', 'Amount', 'Paid']}
					label="Payments needing a refund"
					minWidth="40rem"
					maxRows={8}
					empty="None."
				>
					{#snippet row(payment)}
						<span class="text-base font-semibold text-(--text)" role="cell">{payment.reference}</span>
						<span class="text-base text-(--text)" role="cell">{payment.location_name}</span>
						<span class="text-base text-(--text)" role="cell">{formatMoney(payment.total_cents, payment.currency)}</span>
						<span class="text-base text-(--text)" role="cell">{payment.paid_at ? formatTimestamp(payment.paid_at) : '—'}</span>
					{/snippet}
				</GridTable>
			</div>
		</Card>
	{/if}
</section>
