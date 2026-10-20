<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { setSession, clearSession, auth } from '$lib/auth/state.svelte';
	import { logout as logoutAndLeave } from '$lib/auth/logout';

	import { CalendarDays, House, User } from 'lucide-svelte';

	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Footer from '$lib/components/layout/tenant/Footer.svelte';
	import Sidebar, { type SidebarItem } from '$lib/components/controls/Sidebar.svelte';
	import BottomNav, { type BottomNavItem } from '$lib/components/controls/BottomNav.svelte';
	import Drawer from '$lib/components/overlays/Drawer.svelte';
	import ConfirmDialog from '$lib/components/overlays/ConfirmDialog.svelte';

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

	// Only screens that are built (docs/staff-platform.md lists the rest).
	const staffItems = $derived.by((): SidebarItem[] => [
		{
			label: 'Reviews',
			onclick: () => navigate('/staff/reviews'),
			isActive: isActive('/staff/reviews')
		}
	]);

	const adminItems = $derived.by((): SidebarItem[] => [
		// admin items
	]);

	const isStaff = $derived(
		['staff', 'admin', 'superadmin'].some((role) => $auth.roles.includes(role))
	);

	const isAdmin = $derived(
		['admin', 'superadmin'].some((role) => $auth.roles.includes(role))
	);

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

		// Admins see every staff screen, then their own.
		if (isStaff) {
			result.push(...staffItems);
		}

		if (isAdmin) {
			result.push(...adminItems);
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

	// Customers (only) navigate with a bottom bar on mobile.
	const isCustomerOnly = $derived(
		$auth.roles.includes('customer') && !isStaff
	);

	const bottomNavItems = $derived.by((): BottomNavItem[] => [
		{ label: 'Home', href: route('/home'), icon: House, isActive: isActive('/home') },
		{ label: 'Bookings', href: route('/bookings'), icon: CalendarDays, isActive: isActive('/bookings') },
		{ label: 'Account', href: route('/account'), icon: User, isActive: isActive('/account') }
	]);

	async function logout() {
		isLoggingOut = true;

		try {
			sidebarOpen = false;

			await logoutAndLeave(data.locationCode);
		} finally {
			isLoggingOut = false;
		}
	}
</script>


<!-- Every confirmation in the app (confirmAction). -->
<ConfirmDialog />

{#snippet sidebar()}
	<Sidebar {items} />
{/snippet}

{#snippet bottomNav()}
	<BottomNav items={bottomNavItems} />
{/snippet}

<Layout
	primaryColor={data.location.primary_color}
	secondaryColor={data.location.secondary_color}
	sidebar={$auth.authenticated ? sidebar : undefined}
	bottomNav={$auth.authenticated && isCustomerOnly ? bottomNav : undefined}
>
	{#snippet header()}
		<!-- Customers use the BottomNav on mobile, so no menu. -->
		<Header
			onMenu={isCustomerOnly ? undefined : () => sidebarOpen = true}
		/>
	{/snippet}

	{@render children()}

	{#snippet footer()}
		<Footer />
	{/snippet}
</Layout>

{#if $auth.authenticated && !isCustomerOnly}
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