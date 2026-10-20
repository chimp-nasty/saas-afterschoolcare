<script lang="ts">
    import { page } from "$app/state";

    import Authorize from "$lib/auth/Authorize.svelte";
    import AdminHome from '$lib/features/home/components/AdminHome.svelte';
	import StaffHome from '$lib/features/home/components/StaffHome.svelte';
	import CustomerHome from '$lib/features/home/components/CustomerHome.svelte';
	import Page from '$lib/components/layout/Page.svelte';

	let { data } = $props();
</script>

<Page>
	<Authorize
        locationCode={page.data.locationCode}
        roles={['admin']}
        redirect={false}
    >
        <AdminHome />
    </Authorize>

    <Authorize
        locationCode={page.data.locationCode}
        roles={['staff']}
        excludeRoles={['admin']}
        redirect={false}
    >
        <StaffHome />
    </Authorize>

    <Authorize
        locationCode={page.data.locationCode}
        roles={['customer']}
        excludeRoles={['admin', 'staff']}
        redirect={false}
    >
        <CustomerHome bookings={data.bookings} locationCode={data.locationCode} location={data.location} />
    </Authorize>
</Page>
