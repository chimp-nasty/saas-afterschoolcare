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

	// Only screens that are built (docs/portals.md). The staff portal is
	// every employee's own account; the admin portal runs the business.
	const staffItems = $derived.by((): SidebarItem[] => [
		{
			label: 'My account',
			onclick: () => navigate('/staff/account'),
			isActive: isActive('/staff/account')
		}
	]);

	const adminItems = $derived.by((): SidebarItem[] => [
		{
			label: 'Run sheet',
			onclick: () => navigate('/admin/run-sheet'),
			isActive: isActive('/admin/run-sheet')
		},
		{
			label: 'Families',
			onclick: () => navigate('/admin/families'),
			isActive: isActive('/admin/families')
		},
		{
			label: 'Service days',
			onclick: () => navigate('/admin/sessions'),
			isActive: isActive('/admin/sessions')
		},
		{
			label: 'Medical reviews',
			onclick: () => navigate('/admin/reviews'),
			isActive: isActive('/admin/reviews')
		},
		// Business settings: superadmins only (the API refuses admins too).
		...(isSuperadmin
			? [
					{
						label: 'Service settings',
						onclick: () => navigate('/admin/settings'),
						isActive: isActive('/admin/settings')
					}
				]
			: []),
		{
			label: 'Kiosks',
			onclick: () => navigate('/admin/kiosks'),
			isActive: isActive('/admin/kiosks')
		},
		{
			label: 'Staff',
			onclick: () => navigate('/admin/users'),
			isActive: isActive('/admin/users')
		}
	]);

	const isStaff = $derived(
		['staff', 'admin', 'superadmin'].some((role) => $auth.roles.includes(role))
	);

	const isSuperadmin = $derived($auth.roles.includes('superadmin'));

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
		const result: SidebarItem[] = [];

		// A staff-role login's home is their account, so they get no Home.
		if (isAdmin || !isStaff) {
			result.push({
				label: 'Home',
				onclick: () => navigate('/home'),
				isActive: isActive('/home')
			});
		}

		if (isAdmin) {
			result.push(...adminItems);
		}

		// Everyone who works here, admins included, has their own account.
		if (isStaff) {
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

	// Kiosk tablets (/{location}/kiosk) are full screen: no header,
	// navigation or footer, and no website login involved.
	const isKiosk = $derived(
		page.url.pathname === route('/kiosk') || page.url.pathname.startsWith(`${route('/kiosk')}/`)
	);

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

{#if isKiosk}
	<Layout
		primaryColor={data.location.primary_color}
		secondaryColor={data.location.secondary_color}
	>
		{@render children()}
	</Layout>
{:else}
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

{/if}

{#if $auth.authenticated && !isCustomerOnly && !isKiosk}
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