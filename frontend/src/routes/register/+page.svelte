<!--
    Register a business with its invite (the platform's own site). Once
    registered, the owner logs in on their new site's Business settings:
    the login can't carry over from this site to theirs.
-->
<script lang="ts">
	import { page } from '$app/state';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import RegisterBusinessForm from '$lib/features/platform/components/RegisterBusinessForm.svelte';

	import { createRegistrationApi } from '$lib/api/platform/adapters/platform';
	import type { RegisterTenantRequest } from '$lib/api/schema';

	let { data } = $props();

	const registrationApi = createRegistrationApi();

	// Where the new owner logs in, once registered.
	let loginUrl = $state<string | null>(null);

	// A business's site is its web address before the platform's host.
	const siteSuffix = $derived(`.${page.url.host}`);

	async function register(body: RegisterTenantRequest) {
		const response = await registrationApi.register(body);

		if (response.ok && response.data) {
			loginUrl = response.data.business_login_url;
		}

		return response;
	}
</script>

<main class="p-4">
	<Page>
		<PageHeader title="Register your business" />

		{#if loginUrl}
			<Card border>
				<div class="flex flex-col gap-4">
					<Notice tone="success">Your business is set up. Log in to Business settings to add your centres and connect payments.</Notice>
					<HyperTextLink href={loginUrl}>Go to Business settings</HyperTextLink>
				</div>
			</Card>
		{:else if data.token && data.email}
			<RegisterBusinessForm invite={data.token} email={data.email} {siteSuffix} onsubmit={register} />
		{:else}
			<Notice tone="warning">This invite link can't be used any more. Ask for a new one.</Notice>
		{/if}
	</Page>
</main>
