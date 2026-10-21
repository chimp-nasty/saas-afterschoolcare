<!--
    A child's Medical tab at the staff kiosk, within the staff member's task:
    what the family entered, whether an admin has reviewed it (approved, or
    marked not yet reviewed while it's waiting for re-review), and their
    documents, each opened in a new tab (where it can also be printed).
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';

	import type { ChildMedicalResponse } from '$lib/api/schema';
	import { DOCUMENT_TYPE_LABELS } from '$lib/features/children/documents';
	import { formatTimestamp } from '$lib/utils/helpers';
	import { KIOSK_REVIEW_STATUS } from '../medical';

	let {
		medical,
		error,
		onview
	}: {
		medical: ChildMedicalResponse | null;
		error: string | null;
		onview: (documentId: string) => void;
	} = $props();

	const sections = $derived(
		medical
			? [
					{ label: 'Allergies', value: medical.allergy_info },
					{ label: 'Medical conditions', value: medical.medical_info },
					{ label: 'Medication', value: medical.medication_info }
				].filter((section) => section.value?.trim())
			: []
	);
</script>

{#if error}
	<p class="text-lg font-semibold text-(--danger-text)" role="alert">{error}</p>
{:else if !medical}
	<p class="text-base text-(--text-muted)">Loading medical details…</p>
{:else}
	{@const status = KIOSK_REVIEW_STATUS[medical.review_status]}
	<div class="flex flex-col gap-5">
		<p
			class={[
				'rounded-lg px-4 py-3 text-base font-semibold',
				status.reviewed ? 'bg-(--success-soft) text-(--success-text)' : 'bg-(--warning-soft) text-(--warning-text)'
			]}
		>
			{status.reviewed ? '✓' : '⚠'} {status.label} · {formatTimestamp(medical.status_since)}
		</p>

		{#each sections as section (section.label)}
			<div class="flex flex-col gap-1">
				<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">{section.label}</p>
				<p class="text-base whitespace-pre-line text-(--text)">{section.value}</p>
			</div>
		{:else}
			<p class="text-base text-(--text-muted)">No medical details entered.</p>
		{/each}

		<div class="flex flex-col gap-2">
			<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">Documents</p>

			{#each medical.documents as document (document.id)}
				<div class="grid grid-cols-[1fr_auto] items-center gap-3 border-b border-(--border) pb-2 last:border-b-0">
					<div class="min-w-0">
						<p class="text-base font-semibold text-(--text)">{DOCUMENT_TYPE_LABELS[document.document_type]}</p>
						<p class="truncate text-sm text-(--text-muted)">{document.filename} · uploaded {formatTimestamp(document.created_at)}</p>
					</div>
					<Button variant="ghost" onclick={() => onview(document.id)}>View</Button>
				</div>
			{:else}
				<p class="text-base text-(--text-muted)">No documents.</p>
			{/each}

			{#if medical.documents.length}
				<p class="text-sm text-(--text-muted)">Documents open in a new tab, where they can be printed. Close that tab when you're done.</p>
			{/if}
		</div>
	</div>
{/if}
