<!--
    /{location}/kiosk: both kiosk tablets open this page. It asks the API
    what this tablet is (its device cookie): the family kiosk, the staff
    kiosk, or not set up yet (pairing). No website login is used here; the
    tenant layout shows it full screen (routes/[location_code]/+layout.svelte).
-->
<script lang="ts">
	import { onMount } from 'svelte';

	import FamilyKiosk from '$lib/features/kiosk/components/FamilyKiosk.svelte';
	import KioskScreen from '$lib/features/kiosk/components/KioskScreen.svelte';
	import PairKiosk from '$lib/features/kiosk/components/PairKiosk.svelte';
	import StaffKiosk from '$lib/features/kiosk/components/StaffKiosk.svelte';
	import Button from '$lib/components/actions/Button.svelte';
	import Spinner from '$lib/components/feedback/Spinner.svelte';

	import { createFamilyKioskApi } from '$lib/api/kiosk/adapters/familyKiosk';
	import { createStaffKioskApi } from '$lib/api/kiosk/adapters/staffKiosk';
	import { messageOf } from '$lib/features/kiosk/kiosk';

	let { data } = $props();

	type Kind = 'loading' | 'unpaired' | 'family' | 'staff' | 'error';

	const familyApi = $derived(createFamilyKioskApi(data.locationCode));
	const staffApi = $derived(createStaffKioskApi(data.locationCode));

	let kind = $state<Kind>('loading');
	let problem = $state<string | null>(null);

	const centreName = $derived(data.location.location_name || data.location.tenant_name);

	async function detect() {
		const family = await familyApi.device();

		if (family.ok) {
			kind = 'family';
			return;
		}

		// A paired tablet of the other kind.
		if (family.status === 403 && (await staffApi.device()).ok) {
			kind = 'staff';
			return;
		}

		if (family.status === 401) {
			kind = 'unpaired';
			return;
		}

		problem = messageOf(family);
		kind = 'error';
	}

	async function pair(code: string): Promise<string | null> {
		const response = await familyApi.pair(code);

		if (!response.ok || !response.data) return messageOf(response);

		kind = response.data.kind;
		return null;
	}

	onMount(() => void detect());
</script>

<svelte:head>
	<title>{centreName} kiosk</title>
</svelte:head>

{#if kind === 'staff'}
	<StaffKiosk locationCode={data.locationCode} {centreName} />
{:else}
	<KioskScreen {centreName}>
		{#if kind === 'loading'}
			<div class="flex flex-1 items-center justify-center"><Spinner /></div>
		{:else if kind === 'unpaired'}
			<PairKiosk onpair={pair} />
		{:else if kind === 'family'}
			<FamilyKiosk locationCode={data.locationCode} />
		{:else}
			<div class="flex flex-1 flex-col items-center justify-center gap-4">
				<p class="text-center text-xl font-semibold text-(--danger-text)">{problem}</p>
				<Button variant="ghost" textSize="lg" onclick={() => { kind = 'loading'; void detect(); }}>
					Try again
				</Button>
			</div>
		{/if}
	</KioskScreen>
{/if}
