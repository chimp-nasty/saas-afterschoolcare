<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { setSession, clearSession, auth } from '$lib/auth/state.svelte';
	import { createAuthApi } from '$lib/api/auth/adapters/auth';

	import ResponseToast from '$lib/toast/ResponseToast.svelte';

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

	const locationCode = $derived(
		page.params.location_code
	);

	function route(path: string) {
		return `/${locationCode}${path}`;
	}

	function isActive(path: string) {
		const pathname = route(path);

		return (
			page.url.pathname === pathname ||
			page.url.pathname.startsWith(`${pathname}/`)
		);
	}

	function navigate(path: string) {
		sidebarOpen = false;

		void goto(route(path));
	}

	const adminItems = $derived.by((): SidebarItem[] => [
		// admin items
	]);

	const staffItems = $derived.by((): SidebarItem[] => [
		// staff items
	]);

	const customerItems = $derived.by((): SidebarItem[] => [
		{
			label: 'Account',
			onclick: () => navigate('/account'),
			isActive: isActive('/account')
		},
		{
			label: 'Bookings',
			onclick: () => navigate('/bookings'),
			isActive: isActive('/bookings')
		}
	]);

	const items = $derived.by(() => {
		const result: SidebarItem[] = [
			{
				label: 'Home',
				onclick: () => navigate('/home'),
				isActive: isActive('/home')
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

			await goto(`/${locationCode}/`);
		} finally {
			isLoggingOut = false;
		}
	}
</script>

<ResponseToast />

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
		<Sidebar
			{items}
			drawer
		/>
	</Drawer>
{/if}