<script lang="ts">
    import { page } from "$app/state";

    import Authorize from "$lib/auth/Authorize.svelte";
	import StaffHome from '$lib/features/home/components/StaffHome.svelte';
	import CustomerHome from '$lib/features/home/components/CustomerHome.svelte';
	import Page from '$lib/components/layout/Page.svelte';

	let { data } = $props();

	const STAFF_ROLES = ['staff', 'admin', 'superadmin'];
</script>

<Authorize
    locationCode={page.data.locationCode}
    roles={STAFF_ROLES}
    redirect={false}
>
    <Page width="wide">
        <StaffHome
            locationCode={data.locationCode}
            reviewsWaiting={data.reviewsWaiting ?? 0}
            reviewsRequested={data.reviewsRequested ?? 0}
        />
    </Page>
</Authorize>

<Authorize
    locationCode={page.data.locationCode}
    roles={['customer']}
    excludeRoles={STAFF_ROLES}
    redirect={false}
>
    <Page>
        <CustomerHome bookings={data.bookings} locationCode={data.locationCode} location={data.location} />
    </Page>
</Authorize>
