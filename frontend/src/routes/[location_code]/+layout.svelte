<script lang="ts">
	import { page } from '$app/state';
	import { goto } from '$app/navigation';

	import { setSession, clearSession, auth } from '$lib/auth/state.svelte';
	import { logout as logoutAndLeave } from '$lib/auth/logout';

	import { CalendarDays, House, User } from 'lucide-svelte';

	import Layout from '$lib/components/layout/tenant/Layout.svelte';
	import Header from '$lib/components/layout/tenant/Header.svelte';
	import Footer from '$lib/components/layout/tenant/Footer.svelte';
	import Sidebar, { type SidebarItem, type SidebarSection } from '$lib/components/controls/Sidebar.svelte';
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

	const isStaff = $derived(
		['staff', 'admin', 'superadmin'].some((role) => $auth.roles.includes(role))
	);

	const isSuperadmin = $derived($auth.roles.includes('superadmin'));

	const isAdmin = $derived(
		['admin', 'superadmin'].some((role) => $auth.roles.includes(role))
	);

	const isOwner = $derived(Object.keys($auth.tenantPermissions).length > 0);

	function link(label: string, path: string): SidebarItem {
		return { label, onclick: () => navigate(path), isActive: isActive(path) };
	}

	// Only screens that are built (docs/portals.md). Staff and admins see
	// their links grouped by what they're for, groups and links in
	// alphabetical order; families get a plain list. Home is always first
	// and Logout last.
	const sections = $derived.by((): SidebarSection[] => {
		const groups: SidebarSection[] = [];

		if (isAdmin) {
			groups.push(
				{
					heading: 'Day to day',
					items: [
						link('Kiosks', '/admin/kiosks'),
						link('Run sheet', '/admin/run-sheet'),
						link('Service days', '/admin/sessions')
					]
				},
				{
					heading: 'Families',
					items: [
						link('Families', '/admin/families'),
						link('Medical reviews', '/admin/reviews')
					]
				},
				{
					heading: 'Settings',
					items: [
						// The business's owner: its details, centres and payments.
						...(isOwner
							? [{ label: 'Business settings', onclick: () => { sidebarOpen = false; void goto('/business'); } }]
							: []),
						// Admins see whether payments are on; the owner manages
						// them in Business settings.
						link('Payments', '/admin/payments'),
						// Superadmins only (the API refuses admins too).
						...(isSuperadmin ? [link('Service settings', '/admin/settings')] : []),
						link('Staff', '/admin/users')
					]
				}
			);
		}

		// Everyone who works here, admins included, has their own account.
		if (isStaff) {
			groups.push({ heading: 'Your account', items: [link('My account', '/staff/account')] });
		}

		if ($auth.roles.includes('customer')) {
			const familyItems = [link('Account', '/account'), link('Bookings', '/bookings')];

			// Families only: no headings. Staff who are also a family here get
			// their family's links as a group like the rest.
			groups.push(isStaff ? { heading: 'Your family', items: familyItems } : { items: familyItems });
		}

		groups.sort((a, b) => (a.heading ?? '').localeCompare(b.heading ?? ''));

		for (const group of groups) {
			group.items.sort((a, b) => a.label.localeCompare(b.label));
		}

		return [
			// A staff-role login's home is their account, so they get no Home.
			...(isAdmin || !isStaff ? [{ items: [link('Home', '/home')] }] : []),
			...groups,
			{ items: [{ label: 'Logout', onclick: logout }] }
		];
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
	<Sidebar {sections} />
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
			{sections}
			drawer
		/>
	</Drawer>
{/if}