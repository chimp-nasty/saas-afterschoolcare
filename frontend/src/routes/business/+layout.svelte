<!--
    Business settings (/business): the whole business, run by its owner
    (docs/tenant-administration.md). Outside any centre, under the site's
    own header (docs/public-site.md): sidebar (the header's drawer on mobile), its own
    confirmations, and the login page for anyone without a session.
-->
<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';

	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Sidebar, { type SidebarSection } from '$lib/components/controls/Sidebar.svelte';
	import ConfirmDialog from '$lib/components/overlays/ConfirmDialog.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import { auth, clearSession, setSession } from '$lib/auth/state.svelte';
	import { ABOUT_LINK, BUSINESS_HEADER_LINKS, LOCATIONS_LINK } from '$lib/navigation/siteLinks';

	let { data, children } = $props();

	const isLogin = $derived(page.url.pathname === '/business/login');

	$effect(() => {
		if (data.session) {
			setSession(data.session);
		} else {
			clearSession();
		}
	});

	$effect(() => {
		if (!data.session && !isLogin) {
			void goto('/business/login');
		}
	});

	function isActive(path: string) {
		const pathname = `/business${path}`;

		return path === ''
			? page.url.pathname === '/business'
			: page.url.pathname === pathname || page.url.pathname.startsWith(`${pathname}/`);
	}

	function navigate(path: string) {
		void goto(`/business${path}`);
	}

	async function logout() {
		await createAuthApi().logout();

		clearSession();
		await invalidate('app:session');
		await goto('/business/login');
	}

	// Overview (the home page) first, Logout last, the business's links
	// between in alphabetical order (one group, so no heading).
	const sections = $derived.by((): SidebarSection[] => [
		{ items: [{ label: 'Overview', onclick: () => navigate(''), isActive: isActive('') }] },
		{
			items: [
				{ label: 'Business details', onclick: () => navigate('/settings'), isActive: isActive('/settings') },
				{ label: 'Centres', onclick: () => navigate('/locations'), isActive: isActive('/locations') },
				{ label: 'Domains', onclick: () => navigate('/domains'), isActive: isActive('/domains') },
				{ label: 'Payments', onclick: () => navigate('/payments'), isActive: isActive('/payments') },
				{ label: 'Your site', onclick: () => navigate('/site'), isActive: isActive('/site') }
			]
		},
		{ items: [{ label: 'Logout', onclick: logout }] }
	]);
</script>

<!-- Every confirmation in Business settings (confirmAction). -->
<ConfirmDialog />

{#snippet sidebar()}
	<Sidebar {sections} />
{/snippet}

{#if isLogin}
	<Layout
		primaryColor={data.branding.primaryColor}
		secondaryColor={data.branding.secondaryColor}
		accentColor={data.branding.accentColor}
	>
		{#snippet header()}
			<Header
				homeHref="/"
				title={data.branding.name}
				hasLogo={data.branding.hasLogo}
				links={[LOCATIONS_LINK, ABOUT_LINK]}
			/>
		{/snippet}

		{@render children()}
	</Layout>
{:else if data.session}
	<Layout
		sidebar={sidebar}
		primaryColor={data.branding.primaryColor}
		secondaryColor={data.branding.secondaryColor}
		accentColor={data.branding.accentColor}
	>
		{#snippet header()}
			<Header
				homeHref="/"
				title={data.branding.name}
				hasLogo={data.branding.hasLogo}
				links={BUSINESS_HEADER_LINKS}
				note={`Logged in as ${$auth.firstName ?? $auth.email}`}
				menuSections={[...sections.slice(0, -1), { heading: 'Website', items: BUSINESS_HEADER_LINKS }, ...sections.slice(-1)]}
			/>
		{/snippet}

		{@render children()}
	</Layout>
{/if}
