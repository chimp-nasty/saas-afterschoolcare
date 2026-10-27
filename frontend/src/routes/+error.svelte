<!--
    An error above any location: usually a location that doesn't exist. Not
    found goes to the tenant's page ("/"), never from "/" itself, so it can't
    loop. Anything else is shown, under the site's header like every page:
    the business's (fetched here, since no layout loaded it) or, on the
    platform's own site, the platform's.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import ActionBar from '$lib/components/actions/ActionBar.svelte';
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { page } from '$app/state';
	import { toast } from 'svelte-sonner';

	import Card from '$lib/components/layout/Card.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import PlatformHeader from '$lib/components/layout/PlatformHeader.svelte';
	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';

	import { createLocationBrandingApi } from '$lib/api/tenancy/adapters/location-branding';
	import type { PublicBusinessResponse } from '$lib/api/schema';
	import { ABOUT_LINK, LOCATIONS_LINK } from '$lib/navigation/siteLinks';
	import { isPlatformSite } from '$lib/platform/site';

	const redirects = $derived(page.status === 404 && page.url.pathname !== '/');
	const platform = $derived(isPlatformSite(page.url));

	let business = $state<PublicBusinessResponse | null>(null);

	onMount(() => {
		if (redirects) {
			toast.error("We couldn't find that centre.");
			void goto('/', { replaceState: true });
			return;
		}

		if (!platform) {
			void createLocationBrandingApi()
				.getPublicBusiness()
				.then((response) => {
					business = response.data ?? null;
				});
		}
	});
</script>

{#if !redirects}
	<Layout
		primaryColor={business?.primary_color}
		secondaryColor={business?.secondary_color}
		accentColor={business?.accent_color}
	>
		{#snippet header()}
			{#if platform}
				<PlatformHeader />
			{:else}
				<Header
					homeHref="/"
					title={business?.name ?? ''}
					hasLogo={Boolean(business?.has_logo)}
					links={[LOCATIONS_LINK, ABOUT_LINK]}
				/>
			{/if}
		{/snippet}

		<Page>
			<PageHeader
				title={page.status === 404 ? "We couldn't find that page" : 'Something went wrong'}
				description={page.error?.message}
			/>

			<Card border>
				<p class="text-sm text-(--text-muted)">
					Use the link your centre gave you, or try again in a moment.
				</p>

				{#if page.url.pathname !== '/'}
					<ActionBar start>
						<Button variant="ghost" onclick={() => goto('/')}>Choose your centre</Button>
					</ActionBar>
				{/if}
			</Card>
		</Page>
	</Layout>
{/if}
