<!--
    Business settings › Domains: the business's own domain for its site,
    and up to 4 more sending visitors to it (docs/tenant-administration.md,
    section 7). The owner adds each one and the DNS records it shows; checks
    every few minutes (or Check now) take it live.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';

	import Button from '$lib/components/actions/Button.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import AddDomainForm from '$lib/features/business/components/AddDomainForm.svelte';
	import DomainCard from '$lib/features/business/components/DomainCard.svelte';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import type { AddDomainRequest, DomainResponse } from '$lib/api/schema';

	let { data } = $props();

	const businessApi = createBusinessApi();

	// At most this many domains sending visitors to the main one (the server checks).
	const MAX_REDIRECTS = 4;

	let isChecking = $state(false);

	const listing = $derived(data.domains);

	// Failed and removed domains don't count: another can take their place.
	const inUse = (domain: DomainResponse) => domain.state !== 'failed' && domain.state !== 'removing';

	const mainDomains = $derived(listing?.domains.filter((domain) => domain.is_main) ?? []);
	const redirectDomains = $derived(listing?.domains.filter((domain) => !domain.is_main) ?? []);
	const hasMain = $derived(mainDomains.some(inUse));
	const redirectsInUse = $derived(redirectDomains.filter(inUse).length);

	async function refresh() {
		await invalidate('app:business-domains');
	}

	async function add(body: AddDomainRequest) {
		const response = await businessApi.addDomain(body);

		if (response.ok) await refresh();

		return response;
	}

	async function checkNow() {
		isChecking = true;

		try {
			const response = await businessApi.checkDomains();

			if (response.ok) await refresh();
		} finally {
			isChecking = false;
		}
	}

	async function remove(domain: DomainResponse) {
		await confirmAction({
			title: `Remove ${domain.hostname}?`,
			message: domain.is_main
				? 'Your site goes back to its usual address straight away. Anyone using this domain will find nothing there.'
				: 'It stops sending visitors to your site straight away.',
			confirmLabel: 'Remove',
			tone: 'danger',
			action: async () => {
				const response = await businessApi.removeDomain(domain.id);

				if (response.ok) await refresh();
			}
		});
	}
</script>

<Page width="wide">
	<PageHeader title="Domains" description="Put your site on your own domain, and send other domains you own to it.">
		{#snippet actions()}
			{#if listing?.domains.length}
				<Button variant="ghost" isLoading={isChecking} isDisabled={isChecking} onclick={checkNow}>Check now</Button>
			{/if}
		{/snippet}
	</PageHeader>

	{#if listing}
		<Notice tone={listing.live_domain ? 'success' : 'neutral'}>
			{#if listing.live_domain}
				Your site is at {listing.live_domain}. {listing.generated_host} sends visitors there.
			{:else}
				Your site is at {listing.generated_host}.
			{/if}
		</Notice>

		{#if !listing.available}
			<Notice tone="warning">Custom domains aren't available here yet.</Notice>
		{:else}
			<SectionHeading
				title="Main domain"
				description="Where your site lives. A domain of its own (book.yourbusiness.com.au) or your whole domain."
			/>

			{#each mainDomains as domain (domain.id)}
				<DomainCard {domain} onremove={() => remove(domain)} />
			{/each}

			{#if !hasMain}
				<AddDomainForm isMain={true} onsubmit={add} />
			{/if}

			{#if hasMain || redirectDomains.length}
				<SectionHeading
					title="Domains sending visitors to it"
					description={`Other domains you own, e.g. other endings of your name. Up to ${MAX_REDIRECTS}.`}
				/>

				{#each redirectDomains as domain (domain.id)}
					<DomainCard {domain} onremove={() => remove(domain)} />
				{:else}
					<EmptyState message="None yet." />
				{/each}

				{#if hasMain && redirectsInUse < MAX_REDIRECTS}
					<AddDomainForm isMain={false} onsubmit={add} />
				{/if}
			{/if}
		{/if}
	{/if}
</Page>
