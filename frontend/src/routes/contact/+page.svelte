<!--
    /contact on the platform's own site (docs/platform-site.md): talk to us
    about using Session Pilot for your own business, or about having
    software like it built (by JNB Digital, linked beside the form). What's
    sent is kept for the platform console and emailed to us.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import PlatformHeader from '$lib/components/layout/PlatformHeader.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import PlatformContactForm from '$lib/features/platform/components/PlatformContactForm.svelte';
	import type { PlatformEnquiryTopic } from '$lib/features/platform/enquiries';

	import { createPlatformEnquiriesApi } from '$lib/api/platform/adapters/platformEnquiries';
	import type { SubmitPlatformEnquiryRequest } from '$lib/api/schema';
	import { JNB_DIGITAL_URL, PLATFORM_LINKS } from '$lib/platform/site';

	let { data } = $props();

	const api = createPlatformEnquiriesApi();

	// Starts as the link's topic; the form keeps it in step.
	let topic = $state<PlatformEnquiryTopic | ''>(untrack(() => data.topic as PlatformEnquiryTopic | ''));
	let sent = $state(false);

	async function send(body: SubmitPlatformEnquiryRequest) {
		const response = await api.submit(body);

		if (response.ok) sent = true;

		return response;
	}
</script>

<svelte:head>
	<title>Contact | Session Pilot</title>
</svelte:head>

<Layout>
	{#snippet header()}
		<PlatformHeader links={PLATFORM_LINKS} menuLead={[{ label: 'Log in', href: '/business/login' }]} />
	{/snippet}

	<Page width="wide">
		<PageHeader
			title="Talk to us"
			description="Thinking about Session Pilot for your centres, or want software like it for your own business? Send us a message and we'll get back to you by email."
		/>

		<div class="grid grid-cols-1 gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)] lg:items-start">
			<div class="flex flex-col gap-4">
				{#if sent}
					<Notice tone="success">Thanks, your message is on its way. We'll be in touch soon.</Notice>
				{/if}

				<PlatformContactForm bind:topic onsubmit={send} />
			</div>

			<Card border>
				<div class="flex flex-col gap-3">
					<SectionHeading title="Want software like this built?" />

					<p class="text-base text-(--text)">
						Session Pilot is built by JNB Digital, who design and build custom software for businesses.
					</p>

					{#if topic === 'build_software'}
						<p class="text-sm text-(--text-muted)">Send your message here, or see their work first.</p>
					{/if}

					<HyperTextLink href={JNB_DIGITAL_URL} external>Visit JNB Digital</HyperTextLink>
				</div>
			</Card>
		</div>
	</Page>
</Layout>
