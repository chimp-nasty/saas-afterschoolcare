<!--
    Business settings (/business): the whole business, run by its owner
    (docs/tenant-administration.md). Its own shell, outside any centre:
    sidebar (a drawer on mobile), its own confirmations, and the login page
    for anyone without a session.
-->
<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';

	import { Menu } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Sidebar, { type SidebarSection } from '$lib/components/controls/Sidebar.svelte';
	import Drawer from '$lib/components/overlays/Drawer.svelte';
	import ConfirmDialog from '$lib/components/overlays/ConfirmDialog.svelte';

	import { createAuthApi } from '$lib/api/auth/adapters/auth';
	import { auth, clearSession, setSession } from '$lib/auth/state.svelte';

	let { data, children } = $props();

	let sidebarOpen = $state(false);

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
		sidebarOpen = false;

		void goto(`/business${path}`);
	}

	async function logout() {
		sidebarOpen = false;

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
	<Layout primaryColor={data.branding.primaryColor} secondaryColor={data.branding.secondaryColor}>
		{@render children()}
	</Layout>
{:else if data.session}
	<Layout sidebar={sidebar} primaryColor={data.branding.primaryColor} secondaryColor={data.branding.secondaryColor}>
		{#snippet header()}
			<header class="sticky top-0 z-40 mb-6 w-full border-b border-(--border) bg-(--surface)/90 p-4 backdrop-blur-md">
				<div class="flex min-h-12 w-full items-center gap-4">
					<p class="mr-auto text-sm font-semibold text-(--text)">Business settings</p>

					<p class="hidden text-sm text-(--text-muted) md:block">
						Logged in as {$auth.firstName ?? $auth.email}
					</p>

					<div class="md:hidden">
						<Button variant="ghost" onclick={() => (sidebarOpen = true)} aria-label="Menu">
							<Menu size={20} />
						</Button>
					</div>
				</div>
			</header>
		{/snippet}

		{@render children()}
	</Layout>

	<Drawer open={sidebarOpen} onclose={() => (sidebarOpen = false)}>
		<Sidebar {sections} drawer />
	</Drawer>
{/if}
