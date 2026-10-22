<!--
    Staff's notes about a family's children in Admin › Families, newest
    first: which child, the note, who wrote it and when. Only staff see
    them (here and at the staff kiosk); the family never does. A note can't
    be changed once saved, only deleted.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { ChildNoteResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		notes,
		canAdd,
		onadd,
		ondelete
	}: {
		notes: ChildNoteResponse[];
		// The family has a current child to write about.
		canAdd: boolean;
		onadd: () => void;
		ondelete: (note: ChildNoteResponse) => void;
	} = $props();
</script>

<section class="flex flex-col gap-4">
	<SectionHeading
		title="Notes"
		description="For staff only, here and at the staff kiosk; the family never sees them in the app. A note can't be changed once saved."
	>
		{#snippet actions()}
			<Button onclick={onadd} isDisabled={!canAdd}>Add a note</Button>
		{/snippet}
	</SectionHeading>

	{#if !notes.length}
		<EmptyState message="No notes yet." />
	{:else}
		<div class="flex flex-col gap-4">
			{#each notes as note (note.id)}
				<Card border>
					<div class="flex items-start justify-between gap-4">
						<div class="flex min-w-0 flex-col gap-1">
							<p class="label-text">{note.child_first_name}</p>
							<p class="text-base break-words whitespace-pre-line text-(--text)">{note.note}</p>
							<p class="text-sm text-(--text-muted)">
								{note.created_by ?? 'Former staff'} · {formatTimestamp(note.created_at)}
							</p>
						</div>

						<Button variant="ghost" onclick={() => ondelete(note)}>Delete</Button>
					</div>
				</Card>
			{/each}
		</div>
	{/if}
</section>
