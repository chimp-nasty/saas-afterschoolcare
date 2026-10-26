<!--
    One custom domain (Business settings › Domains): how far it's got, what
    to do next, the DNS records it needs, and Remove.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import Pill from '$lib/components/text/Pill.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import DnsRecords from '$lib/features/business/components/DnsRecords.svelte';
	import { DOMAIN_STATES } from '$lib/features/business/domains';

	import type { DomainResponse } from '$lib/api/schema';
	import { formatTimestamp } from '$lib/utils/helpers';

	let {
		domain,
		onremove
	}: {
		domain: DomainResponse;
		onremove: () => void;
	} = $props();

	const state = $derived(DOMAIN_STATES[domain.state]);
</script>

<Card border>
	<div class="flex flex-col gap-4">
		<SectionHeading
			title={domain.include_www ? `${domain.hostname} (and www)` : domain.hostname}
			description={domain.last_checked_at ? `Last checked ${formatTimestamp(domain.last_checked_at)}.` : 'Not checked yet.'}
		>
			{#snippet actions()}
				<Pill tone={state.tone}>{state.label}</Pill>
			{/snippet}
		</SectionHeading>

		<Notice tone={state.tone}>
			{domain.failure_reason ? `${domain.failure_reason} ` : ''}{state.help}
		</Notice>

		{#if domain.state !== 'removing'}
			<DnsRecords records={domain.records} />

			<div>
				<Button variant="ghost" onclick={onremove}>Remove</Button>
			</div>
		{/if}
	</div>
</Card>
