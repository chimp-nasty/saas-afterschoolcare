<!--
    Platform › Businesses: every business on the platform, with its web
    address, centres and whether it takes payments, to switch off or on.
    Nothing of a business's families, bookings or staff.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';

	import Button from '$lib/components/actions/Button.svelte';
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';
	import Pill from '$lib/components/text/Pill.svelte';

	import { createPlatformApi } from '$lib/api/platform/adapters/platform';
	import type { PlatformTenantResponse } from '$lib/api/schema';
	import { formatTimestampDDMMYYYY } from '$lib/utils/helpers';

	let { data } = $props();

	const platformApi = createPlatformApi();

	async function switchOff(tenant: PlatformTenantResponse) {
		await confirmAction({
			title: `Switch ${tenant.name} off?`,
			message: "Its site and logins stop working, as if it didn't exist. Its data and bookings are kept, and payments already under way still settle. You can switch it back on.",
			confirmLabel: 'Switch off',
			tone: 'danger',
			action: async () => {
				const response = await platformApi.setTenantActive(tenant.id, false);

				if (response.ok) await invalidate('app:platform-tenants');
			}
		});
	}

	async function switchOn(tenant: PlatformTenantResponse) {
		const response = await platformApi.setTenantActive(tenant.id, true);

		if (response.ok) await invalidate('app:platform-tenants');
	}
</script>

<Page width="wide">
	<PageHeader title="Businesses" description="Every business on the platform. Invite a new one from Invites." />

	<GridTable
		items={data.tenants}
		key={(tenant) => tenant.id}
		columns="minmax(10rem,1.5fr) minmax(8rem,1fr) minmax(12rem,1.5fr) 6rem 9rem 11rem 9rem"
		headers={['Business', 'Web address', 'Invited as', 'Centres', 'Payments', 'Joined', '']}
		label="Businesses"
		empty="No businesses yet."
	>
		{#snippet row(tenant)}
			<span class="font-semibold">{tenant.name}</span>
			<span class="text-sm text-(--text-muted)">
				{tenant.custom_domain ?? tenant.code}{#if tenant.domains_in_progress}&nbsp;· {tenant.domains_in_progress} setting up{/if}
			</span>
			<span class="text-sm">{tenant.invited_email ?? '—'}</span>
			<span>{tenant.location_count}</span>
			<span>
				{#if !tenant.is_active}
					<Pill tone="neutral">Switched off</Pill>
				{:else if tenant.takes_payments}
					<Pill tone="success">Taking</Pill>
				{:else if tenant.payments_connected}
					<Pill tone="warning">Not ready</Pill>
				{:else}
					<Pill tone="warning">Not connected</Pill>
				{/if}
			</span>
			<span class="text-sm">{formatTimestampDDMMYYYY(tenant.created_at)}</span>
			<span>
				{#if tenant.is_active}
					<Button variant="ghost" onclick={() => switchOff(tenant)}>Switch off</Button>
				{:else}
					<Button variant="ghost" onclick={() => switchOn(tenant)}>Switch on</Button>
				{/if}
			</span>
		{/snippet}
	</GridTable>
</Page>
