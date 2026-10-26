<!--
    The DNS records a custom domain needs (Business settings › Domains): what
    each is for, its name and value with a copy button each (they're long),
    and whether the last check found it.
-->
<script lang="ts">
	import { toast } from 'svelte-sonner';

	import Button from '$lib/components/actions/Button.svelte';
	import Pill from '$lib/components/text/Pill.svelte';

	import type { DnsRecordResponse } from '$lib/api/schema';

	let { records }: { records: DnsRecordResponse[] } = $props();

	async function copy(text: string, what: string) {
		await navigator.clipboard.writeText(text);
		toast.success(`${what} copied`);
	}
</script>

<ul class="flex flex-col gap-4">
	{#each records as record (`${record.type} ${record.name}`)}
		<li class="flex flex-col gap-2 border-b border-(--border) pb-4 last:border-b-0 last:pb-0">
			<div class="flex flex-wrap items-center justify-between gap-2">
				<p class="text-sm text-(--text-muted)">
					<span class="font-semibold text-(--text)">{record.type}</span>: {record.purpose}
				</p>

				{#if record.seen}
					<Pill tone="success">Found</Pill>
				{:else}
					<Pill tone="neutral">Not found yet</Pill>
				{/if}
			</div>

			{#each [{ label: 'Name', text: record.name }, { label: 'Value', text: record.value }] as part (part.label)}
				<div class="flex items-center gap-3">
					<div class="flex min-w-0 flex-1 flex-col">
						<span class="label-text">{part.label}</span>
						<span class="break-all font-mono text-sm text-(--text)">{part.text}</span>
					</div>

					<Button variant="ghost" onclick={() => copy(part.text, part.label)}>Copy</Button>
				</div>
			{/each}
		</li>
	{/each}
</ul>
