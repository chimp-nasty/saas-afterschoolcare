<!--
    The messages sent to a family in Admin › Families, newest first: the
    title, which child (if any), the text, who sent it and when, and
    whether the family has read it. Messages from the centre's own steps
    (e.g. a medical review's "documents needed") are listed too. An unread
    message can be withdrawn.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Pill from '$lib/components/text/Pill.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { FamilyMessageResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		messages,
		onsend,
		onwithdraw
	}: {
		messages: FamilyMessageResponse[];
		onsend: () => void;
		onwithdraw: (message: FamilyMessageResponse) => void;
	} = $props();
</script>

<section class="flex flex-col gap-4">
	<SectionHeading
		title="Messages"
		description="For things only this family needs to know or do. Confirmations and medical review requests are already sent automatically. The family reads messages in their account and is emailed that there's one, never what it says."
	>
		{#snippet actions()}
			<Button onclick={onsend}>Send a message</Button>
		{/snippet}
	</SectionHeading>

	{#if !messages.length}
		<EmptyState message="No messages yet." />
	{:else}
		<div class="flex flex-col gap-4">
			{#each messages as message (message.id)}
				<Card border>
					<div class="flex items-start justify-between gap-4">
						<div class="flex min-w-0 flex-col gap-1">
							<div class="flex flex-wrap items-center gap-2">
								<p class="text-base font-semibold text-(--text)">{message.title}</p>
								{#if message.cited_at}
									<Pill tone="success">Read</Pill>
								{:else}
									<Pill tone="warning">Not read</Pill>
								{/if}
							</div>
							{#if message.child_first_name}
								<p class="label-text">About {message.child_first_name}</p>
							{/if}
							<p class="text-base break-words whitespace-pre-line text-(--text)">{message.message}</p>
							<p class="text-sm text-(--text-muted)">
								{message.created_by ?? 'Former staff'} · {formatTimestamp(message.created_at)}
								{#if message.cited_at}
									· read {formatTimestamp(message.cited_at)}
								{/if}
							</p>
						</div>

						{#if !message.cited_at}
							<Button variant="ghost" onclick={() => onwithdraw(message)}>Withdraw</Button>
						{/if}
					</div>
				</Card>
			{/each}
		</div>
	{/if}
</section>
