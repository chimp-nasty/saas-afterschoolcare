<!--
    Business settings › Edit a centre. Changing its web address moves it:
    old links and bookmarks (emails, the kiosk tablets) then lead to your
    site's home page, where families choose the centre again.
-->
<script lang="ts">
	import { goto, invalidate } from '$app/navigation';

	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';
	import LocationForm from '$lib/features/business/components/LocationForm.svelte';

	import { createBusinessApi } from '$lib/api/tenancy/adapters/business';
	import type { BusinessLocationRequest } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';

	let { data } = $props();

	const businessApi = createBusinessApi();

	const initial = $derived.by((): BusinessLocationRequest | undefined => {
		const location = data.location;

		if (!location) return undefined;

		return {
			name: location.name,
			code: location.code,
			address_line_1: location.address_line_1,
			address_line_2: location.address_line_2,
			suburb: location.suburb,
			state: location.state as BusinessLocationRequest['state'],
			postcode: location.postcode,
			phone: location.phone,
			email: location.email,
			timezone: location.timezone as BusinessLocationRequest['timezone']
		};
	});

	const notSaved: ApiResponse<unknown> = { ok: false, msg: '', data: null, status: 0, fieldErrors: {} };

	async function save(body: BusinessLocationRequest) {
		if (!data.location) return notSaved;

		if (body.code !== data.location.code) {
			const confirmed = await confirmAction({
				title: "Change this centre's web address?",
				message: `It moves from /${data.location.code} to /${body.code}. Old links and bookmarks, including emails already sent and the kiosk tablets, will lead to your site's home page instead; reopen the kiosks at the new address.`,
				confirmLabel: 'Change address'
			});

			if (!confirmed) return notSaved;
		}

		const response = await businessApi.updateLocation(data.location.id, body);

		if (response.ok) {
			await invalidate('app:business');
			await goto('/business/locations');
		}

		return response;
	}
</script>

<Page>
	<PageHeader title={data.location?.name ?? 'Centre'} />

	{#if initial}
		<LocationForm {initial} submitLabel="Save centre" onsubmit={save} />
	{/if}

	<HyperTextLink href="/business/locations">Back to centres</HyperTextLink>
</Page>
