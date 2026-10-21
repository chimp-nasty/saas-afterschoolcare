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

	const columns =
		'grid grid-cols-[minmax(10rem,1.5fr)_minmax(10rem,1.5fr)_minmax(8rem,1fr)_minmax(10rem,1.2fr)_6rem] items-center gap-x-4';
	const headers = ['Child', 'Plan', 'Updated', 'Printed', ''];
</script>

<div class="flex flex-col gap-4">
	<div class="flex flex-wrap items-end justify-between gap-4">
		<div class="flex flex-col gap-1">
			<h2 class="text-lg font-extrabold text-(--text)">Action plans</h2>
			<p class="text-base text-(--text-muted)">
				The folder copy of every child's plan. NEW plans need their printed copy replaced.
			</p>
		</div>

		{#if plans}
			<div class="flex items-center gap-3">
				{#if shownTo}<span class="text-base text-(--text-muted)">Shown to {shownTo}</span>{/if}
				<Button variant="ghost" onclick={onhide}>Hide</Button>
			</div>
		{:else}
			<Button onclick={onshow}>Show action plans</Button>
		{/if}
	</div>

	{#if plans}
		<div class="overflow-x-auto rounded-2xl border border-(--border) bg-(--surface)">
			<div class="min-w-[52rem]" role="table" aria-label="Action plans">
				<div class={[columns, 'border-b border-(--border) bg-(--surface-muted) px-5 py-2']} role="row">
					{#each headers as header, index (index)}
						<span class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)" role="columnheader">{header}</span>
					{/each}
				</div>

				{#each plans as plan (plan.document_id)}
					<div class={[columns, 'min-h-12 border-b border-(--border) px-5 py-2 last:border-b-0']} role="row">
						<span class="truncate text-base font-semibold text-(--text)" role="cell">
							{plan.child_first_name} {plan.child_last_name}
						</span>
						<span class="text-base text-(--text)" role="cell">{DOCUMENT_TYPE_LABELS[plan.document_type]}</span>
						<span class="flex flex-wrap items-center gap-2 text-base text-(--text)" role="cell">
							{formatTimestamp(plan.uploaded_at)}
							{#if plan.is_new}
								<span class="rounded-full bg-(--warning-soft) px-2 py-0.5 text-xs font-extrabold uppercase tracking-wide text-(--warning-text)">New</span>
							{/if}
						</span>
						<span role="cell">
							<label class="flex min-h-12 items-center gap-2">
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
					</div>
				{:else}
					<p class="px-5 py-3 text-base text-(--text-muted)">No children have an action plan.</p>
				{/each}
			</div>
		</div>

		<p class="text-sm text-(--text-muted)">Plans open in a new tab, where they can be printed. Close that tab when you're done.</p>
	{:else}
		<Card border>
			<p class="text-base text-(--text-muted)">Choose Show action plans and enter your PIN to see the list.</p>
		</Card>
	{/if}
</div>
