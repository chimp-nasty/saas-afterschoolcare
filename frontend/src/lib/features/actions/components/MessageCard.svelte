<!--
    One message from the centre in the family's account: its title, when it
    was sent, and the whole message. When it's about a page in their account
    (e.g. a child's documents) there's a "Go to section" button, which also
    marks it read; an unread message can be marked read on its own.
-->
<script lang="ts">
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	import type { ActionResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		message,
		href,
		busy = false,
		onopen,
		onread
	}: {
		message: ActionResponse;
		// Where its link goes; null for a plain message.
		href: string | null;
		busy?: boolean;
		onopen: (message: ActionResponse, href: string) => void;
		onread: (message: ActionResponse) => void;
	} = $props();

	const unread = $derived(!message.cited_at);
</script>

<Card border>
	<div class="flex flex-col gap-4">
		<SectionHeading title={message.title} description={`Sent ${formatTimestamp(message.created_at)}`} />

		<p class="text-base break-words whitespace-pre-line text-(--text)">{message.message}</p>

		{#if href || unread}
			<ActionBar>
				{#if unread}
					<Button variant={href ? 'ghost' : 'default'} isLoading={busy} onclick={() => onread(message)}>Mark as read</Button>
				{/if}
				{#if href}
					<Button isLoading={busy} onclick={() => onopen(message, href)}>Go to section</Button>
				{/if}
			</ActionBar>
		{/if}
	</div>
</Card>
