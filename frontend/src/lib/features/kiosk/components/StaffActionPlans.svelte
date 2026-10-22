<!--
    The staff kiosk's Medical tab: the action plan list that keeps the
    physical folder current. It's medical information, so it's behind a
    staff member's PIN and hidden again when their task ends. Every active
    child's plan, by name; NEW means replace the folder copy (not yet
    reviewed by an admin, or uploaded in the last 7 days). Plans open in a
    new tab, where they can be printed; Printed records that the folder copy
    is done (by whoever's PIN opened the list).
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import Pill from '$lib/components/text/Pill.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { ActionPlanResponse } from '$lib/api/schema';
	import { DOCUMENT_TYPE_LABELS } from '$lib/features/children/documents';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		plans,
		shownTo,
		onshow,
		onhide,
		onview,
		onprinted
	}: {
		// Null until someone enters their PIN.
		plans: ActionPlanResponse[] | null;
		shownTo: string | null;
		onshow: () => void;
		onhide: () => void;
		onview: (documentId: string) => void;
		onprinted: (documentId: string, printed: boolean) => void;
	} = $props();

	const columns = 'minmax(10rem,1.5fr) minmax(10rem,1.5fr) minmax(8rem,1fr) minmax(10rem,1.2fr) 6rem';
	const headers = ['Child', 'Plan', 'Updated', 'Printed', ''];
</script>

<div class="flex flex-col gap-4">
	<SectionHeading
		size="kiosk"
		title="Action plans"
		description="The folder copy of every child's plan. NEW plans need their printed copy replaced."
	>
		{#snippet actions()}
			{#if plans}
				{#if shownTo}<span class="text-lg text-(--text-muted)">Shown to {shownTo}</span>{/if}
				<Button variant="ghost" onclick={onhide}>Hide</Button>
			{:else}
				<Button onclick={onshow}>Show action plans</Button>
			{/if}
		{/snippet}
	</SectionHeading>

	{#if plans}
		<GridTable
			items={plans}
			key={(plan) => plan.document_id}
			{columns}
			{headers}
			label="Action plans"
			minWidth="52rem"
			empty="No children have an action plan."
		>
			{#snippet row(plan)}
				<span class="text-base font-semibold text-(--text)" role="cell">{plan.child_first_name} {plan.child_last_name}</span>
				<span class="text-base text-(--text)" role="cell">{DOCUMENT_TYPE_LABELS[plan.document_type]}</span>
				<span class="flex items-center gap-2 text-base text-(--text)" role="cell">
					{formatTimestamp(plan.uploaded_at)}
					{#if plan.is_new}
						<Pill tone="warning" size="kiosk">New</Pill>
					{/if}
				</span>
				<span role="cell">
					<label class="flex h-12 items-center gap-2">
						<input
							type="checkbox"
							class="size-5 shrink-0"
							checked={!!plan.printed_at}
							onchange={(event) => onprinted(plan.document_id, event.currentTarget.checked)}
						/>
						<span class="truncate text-sm text-(--text-muted)">
							{plan.printed_at ? `${plan.printed_by ?? 'Staff'} · ${formatTimestamp(plan.printed_at)}` : 'Not printed'}
						</span>
					</label>
				</span>
				<span role="cell">
					<Button variant="ghost" fullWidth onclick={() => onview(plan.document_id)}>View</Button>
				</span>
			{/snippet}
		</GridTable>

		<p class="text-sm text-(--text-muted)">Plans open in a new tab, where they can be printed. Close that tab when you're done.</p>
	{:else}
		<Card border>
			<p class="text-lg text-(--text-muted)">Choose Show action plans and enter your PIN to see the list.</p>
		</Card>
	{/if}
</div>
