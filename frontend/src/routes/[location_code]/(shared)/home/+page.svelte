<script lang="ts">
    import { page } from "$app/state";

    import Authorize from "$lib/auth/Authorize.svelte";   
    import AdminHome from '$lib/features/home/components/AdminHome.svelte';
	import StaffHome from '$lib/features/home/components/StaffHome.svelte';
	import CustomerHome from '$lib/features/home/components/CustomerHome.svelte';

	function getWeekDate(dayIndex: number): string {
		const date = new Date();
		const day = date.getDay();

		const distanceToMonday =
			day === 0
				? -6
				: 1 - day;

		date.setDate(
			date.getDate() +
			distanceToMonday +
			dayIndex
		);

		const year = date.getFullYear();
		const month = String(date.getMonth() + 1).padStart(2, '0');
		const dateNumber = String(date.getDate()).padStart(2, '0');

		return `${year}-${month}-${dateNumber}`;
	}

    // temp data
	const bookings = [
		// Monday
		{
			id: '1',
			serviceDate: getWeekDate(0),
			serviceCode: 'BSC',
			serviceLabel: 'Before School Care',
			childId: 'child-1',
			childFirstName: 'Paxton'
		},

		// Tuesday — all 3 children, both services
		{
			id: '2',
			serviceDate: getWeekDate(1),
			serviceCode: 'BSC',
			serviceLabel: 'Before School Care',
			childId: 'child-1',
			childFirstName: 'Paxton'
		},
		{
			id: '3',
			serviceDate: getWeekDate(1),
			serviceCode: 'ASC',
			serviceLabel: 'After School Care',
			childId: 'child-1',
			childFirstName: 'Paxton'
		},
		{
			id: '4',
			serviceDate: getWeekDate(1),
			serviceCode: 'BSC',
			serviceLabel: 'Before School Care',
			childId: 'child-2',
			childFirstName: 'Harper'
		},
		{
			id: '5',
			serviceDate: getWeekDate(1),
			serviceCode: 'ASC',
			serviceLabel: 'After School Care',
			childId: 'child-2',
			childFirstName: 'Harper'
		},
		{
			id: '6',
			serviceDate: getWeekDate(1),
			serviceCode: 'BSC',
			serviceLabel: 'Before School Care',
			childId: 'child-3',
			childFirstName: 'Charlie'
		},
		{
			id: '7',
			serviceDate: getWeekDate(1),
			serviceCode: 'ASC',
			serviceLabel: 'After School Care',
			childId: 'child-3',
			childFirstName: 'Charlie'
		},

		// Wednesday
		{
			id: '8',
			serviceDate: getWeekDate(2),
			serviceCode: 'ASC',
			serviceLabel: 'After School Care',
			childId: 'child-2',
			childFirstName: 'Harper'
		},

		// Thursday
		{
			id: '9',
			serviceDate: getWeekDate(3),
			serviceCode: 'BSC',
			serviceLabel: 'Before School Care',
			childId: 'child-3',
			childFirstName: 'Charlie'
		},

		// Friday
		{
			id: '10',
			serviceDate: getWeekDate(4),
			serviceCode: 'ASC',
			serviceLabel: 'After School Care',
			childId: 'child-1',
			childFirstName: 'Paxton'
		}
	];
</script>

<div class="flex w-full max-w-xl flex-1 flex-col">
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
        <CustomerHome {bookings}/>
    </Authorize>
</div>