<!--
    A child's Notes tab at the staff kiosk, within the staff member's task:
    staff's notes about the child, newest first, with who wrote each and
    when. Read-only: admins write them on the website. Never shown to the
    family.
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';

	import type { ChildNoteResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		notes,
		error
	}: {
		notes: ChildNoteResponse[] | null;
		error: string | null;
	} = $props();
</script>

{#if error}
	<ErrorText size="kiosk" message={error} />
{:else if !notes}
	<p class="text-lg text-(--text-muted)">Loading notes…</p>
{:else if !notes.length}
	<EmptyState size="kiosk" message="No notes about this child." />
{:else}
	<div class="flex flex-col gap-4">
		{#each notes as note (note.id)}
			<Card border>
				<div class="flex flex-col gap-1">
					<p class="text-lg break-words whitespace-pre-line text-(--text)">{note.note}</p>
					<p class="text-lg text-(--text-muted)">
						{note.created_by ?? 'Former staff'} · {formatTimestamp(note.created_at)}
					</p>
				</div>
			</Card>
		{/each}
	</div>
{/if}
