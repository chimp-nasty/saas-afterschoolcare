<!--
    A child's current documents, each with View and Remove. The page opens
    and removes them.
-->
<script lang="ts">
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';

	import type { ChildDocumentResponse } from '$lib/api/schema';
	import { DOCUMENT_TYPE_LABELS, formatFileSize } from '$lib/features/children/documents';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		documents,
		firstName,
		onview,
		onremove,
		empty
	}: {
		documents: ChildDocumentResponse[];
		firstName: string;
		onview: (document: ChildDocumentResponse) => void | Promise<void>;
		// Families only; staff see the documents without it.
		onremove?: (document: ChildDocumentResponse) => void | Promise<void>;
		// Shown when there are none (defaults to the family's wording).
		empty?: string;
	} = $props();

	let opening = $state<string | null>(null);

	async function view(document: ChildDocumentResponse) {
		opening = document.id;

		try {
			await onview(document);
		} finally {
			opening = null;
		}
	}
</script>

<div class="flex flex-col gap-4">
	{#each documents as document (document.id)}
		<Card border>
			<div class="flex flex-col gap-4">
				<div class="flex min-w-0 flex-col gap-1">
					<p class="text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">
						{DOCUMENT_TYPE_LABELS[document.document_type]}
					</p>

					<p class="text-base font-semibold text-(--text) wrap-break-word">
						{document.filename}
					</p>

					<p class="text-sm text-(--text-muted)">
						Added {formatTimestamp(document.created_at)}{document.size_bytes
							? ` · ${formatFileSize(document.size_bytes)}`
							: ''}
					</p>
				</div>

				<ActionBar>
					{#if onremove}
						<Button variant="ghost" onclick={() => onremove(document)}>
							Remove
						</Button>
					{/if}

					<Button
						variant="ghost"
						isLoading={opening === document.id}
						isDisabled={opening === document.id}
						onclick={() => view(document)}
					>
						View
					</Button>
				</ActionBar>
			</div>
		</Card>
	{:else}
		<p class="text-sm text-(--text-muted)">
			{empty ??
				`No documents yet. Upload ${firstName}'s action plans and any other medical documents the centre needs here.`}
		</p>
	{/each}
</div>
