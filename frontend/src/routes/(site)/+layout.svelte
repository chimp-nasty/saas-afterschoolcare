<!--
    The business's pages (/, /locations, /about; docs/public-site.md): its
    colours, the header and the footer with its policies. The header has no
    Programs, Log in or Enrol now: those belong to a centre, so they're on
    its pages. On the platform's own site, the platform's header instead.
-->
<script lang="ts">
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import PlatformHeader from '$lib/components/layout/PlatformHeader.svelte';

	import { siteFileUrl } from '$lib/api/tenancy/adapters/location-branding';
	import { ABOUT_LINK, BUSINESS_LINK, LOCATIONS_LINK } from '$lib/navigation/siteLinks';
	import { PLATFORM_LINKS } from '$lib/platform/site';

	let { data, children } = $props();

	const business = $derived(data.business);
	const name = $derived(business?.name ?? data.locations[0]?.tenant_name ?? 'Choose your centre');

	const headerLinks = $derived([LOCATIONS_LINK, ABOUT_LINK, ...(data.isOwner ? [BUSINESS_LINK] : [])]);
</script>

{#if data.platform}
	<!-- The platform's own home page: its own header, no business, its
	     landing page in full-width bands. -->
	<Layout flush>
		{#snippet header()}
			<!-- Log in is a stub: business logins only work on a business's own
			     site ({tenant}.{base domain}/business/login) for now. -->
			<PlatformHeader links={PLATFORM_LINKS} menuLead={[{ label: 'Log in', href: '/business/login' }]} />
		{/snippet}

		{@render children()}
	</Layout>
{:else}
	<Layout
		flush
		primaryColor={business?.primary_color}
		secondaryColor={business?.secondary_color}
		accentColor={business?.accent_color}
	>
		{#snippet header()}
			<Header
				homeHref="/"
				title={name}
				hasLogo={Boolean(business?.has_logo)}
				links={headerLinks}
				flush
			/>
		{/snippet}

		{@render children()}

		{#snippet footer()}
			<div class="w-full border-t border-(--border) bg-(--surface) px-4 py-8">
				<div class="mx-auto flex max-w-6xl flex-col gap-2 md:flex-row md:items-center md:justify-between">
					<p class="text-sm text-(--text-muted)">© {new Date().getFullYear()} {name}</p>

					{#if business?.has_privacy || business?.has_terms}
						<div class="flex flex-wrap gap-x-5">
							{#if business.has_privacy}
								<HyperTextLink href={siteFileUrl('privacy')} external>Privacy policy</HyperTextLink>
							{/if}
							{#if business.has_terms}
								<HyperTextLink href={siteFileUrl('terms')} external>Terms</HyperTextLink>
							{/if}
						</div>
					{/if}
				</div>
			</div>
		{/snippet}
	</Layout>
{/if}
