<!--
    The platform console (/platform, the platform's own site): businesses
    and invites (docs/tenant-administration.md, stage 4). Its own shell and
    login, apart from any tenant's.
-->
<script lang="ts">
	import { page } from '$app/state';
	import { goto, invalidate } from '$app/navigation';

	import PlatformHeader from '$lib/components/layout/PlatformHeader.svelte';
	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Sidebar, { type SidebarSection } from '$lib/components/controls/Sidebar.svelte';
	import Drawer from '$lib/components/overlays/Drawer.svelte';
	import ConfirmDialog from '$lib/components/overlays/ConfirmDialog.svelte';

	import { createPlatformApi } from '$lib/api/platform/adapters/platform';

	let { data, children } = $props();

	let sidebarOpen = $state(false);

	const isLogin = $derived(page.url.pathname === '/platform/login');

	$effect(() => {
		if (!data.session && !isLogin) {
			void goto('/platform/login');
		}
	});

	function isActive(path: string) {
		return page.url.pathname === `/platform${path}`;
	}

	function navigate(path: string) {
		sidebarOpen = false;

		void goto(`/platform${path}`);
	}

	async function logout() {
		sidebarOpen = false;

		await createPlatformApi().logout();
		await invalidate('app:platform-session');
		await goto('/platform/login');
	}

	const sections = $derived.by((): SidebarSection[] => [
		{
			items: [
				{ label: 'Businesses', onclick: () => navigate(''), isActive: isActive('') },
				{ label: 'Invites', onclick: () => navigate('/invites'), isActive: isActive('/invites') }
			]
		},
		{ items: [{ label: 'Logout', onclick: logout }] }
	]);
</script>

<!-- Every confirmation in the console (confirmAction). -->
<ConfirmDialog />

{#snippet sidebar()}
	<Sidebar {sections} />
{/snippet}

{#if isLogin}
	<Layout>
		{#snippet header()}
			<PlatformHeader />
		{/snippet}

		{@render children()}
	</Layout>
{:else if data.session}
	<Layout sidebar={sidebar}>
		{#snippet header()}
			<PlatformHeader note={`Logged in as ${data.session?.email}`} onMenu={() => (sidebarOpen = true)} />
		{/snippet}

		{@render children()}
	</Layout>

	<Drawer open={sidebarOpen} onclose={() => (sidebarOpen = false)}>
		<Sidebar {sections} drawer />
	</Drawer>
{/if}
