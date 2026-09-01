<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { setSession, clearSession, auth } from '$lib/auth/state.svelte';
	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Footer from '$lib/components/layout/tenant/Footer.svelte';
	import Sidebar, { type SidebarItem } from '$lib/components/controls/Sidebar.svelte';
	import Drawer from '$lib/components/overlays/Drawer.svelte';

	let { data, children } = $props();

	let sidebarOpen = $state(false);
	let isLoggingOut = $state(false);

	$effect(() => {
		if (data.session) {
			setSession(data.session);
		} else {
			clearSession();
		}
	});

	const adminItems: SidebarItem[] = [

	];

	const staffItems: SidebarItem[] = [

	];

	const customerItems: SidebarItem[] = [

	];

	const items = $derived.by(() => {
		const result: SidebarItem[] = [
			{
				label: 'Home',
				href: `/${page.params.location_code}/home`
			}
		];

		if ($auth.roles.includes('admin')) {
			result.push(...adminItems);
		}

		if ($auth.roles.includes('staff')) {
			result.push(...staffItems);
		}

		if ($auth.roles.includes('customer')) {
			result.push(...customerItems);
		}

		result.push({
			label: 'Logout',
			onclick: logout
		});

		return result;
	});

	async function logout() {
		isLoggingOut = true;

		try {
			const authApi = createAuthApi();

			await authApi.logout();

			clearSession();
			sidebarOpen = false;

			await goto(`/${page.params.location_code}/`);
		} finally {
			isLoggingOut = false;
		}
	}
</script>

{#snippet sidebar()}
	<Sidebar {items} />
{/snippet}

<Layout
	primaryColor={data.location.primary_color}
	secondaryColor={data.location.secondary_color}
	sidebar={$auth.authenticated ? sidebar : undefined}
>
	{#snippet header()}
		<Header
			onMenu={() => sidebarOpen = true}
		/>
	{/snippet}

	{@render children()}

	{#snippet footer()}
		<Footer />
	{/snippet}
</Layout>

{#if $auth.authenticated}
	<Drawer
		open={sidebarOpen}
		onclose={() => sidebarOpen = false}
	>
		{@render sidebar()}
	</Drawer>
{/if}