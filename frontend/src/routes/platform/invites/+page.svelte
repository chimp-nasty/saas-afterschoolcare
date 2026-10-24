<!--
    Platform › Invites: a one-time registration link for a business's
    owner, to send them yourself (no email yet). The link is shown once:
    only its hash is kept. Pending invites can be revoked; they expire
    after a week.
-->
<script lang="ts">
	import { invalidate } from '$app/navigation';
	import { toast } from 'svelte-sonner';

	import Button from '$lib/components/actions/Button.svelte';
	import Card from '$lib/components/layout/Card.svelte';
	import GridTable from '$lib/components/layout/GridTable.svelte';
	import Page from '$lib/components/layout/Page.svelte';
	import PageHeader from '$lib/components/layout/PageHeader.svelte';
	import { confirmAction } from '$lib/components/overlays/confirm.svelte';
	import Notice from '$lib/components/text/Notice.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';
	import InviteForm from '$lib/features/platform/components/InviteForm.svelte';

	import { createPlatformApi } from '$lib/api/platform/adapters/platform';
	import type { CreatedInviteResponse, CreateInviteRequest, InviteResponse } from '$lib/api/schema';
	import { formatTimestampDDMMYYYY } from '$lib/utils/helpers';

	let { data } = $props();

	const platformApi = createPlatformApi();

	// The link just made: shown until the page is left.
	let created = $state<CreatedInviteResponse | null>(null);

	async function create(body: CreateInviteRequest) {
		const response = await platformApi.createInvite(body);

		if (response.ok && response.data) {
			created = response.data;
			await invalidate('app:platform-invites');
		}

		return response;
	}

	async function copyLink() {
		if (!created) return;

		await navigator.clipboard.writeText(created.url);
		toast.success('Link copied');
	}

	async function revoke(invite: InviteResponse) {
		await confirmAction({
			title: `Revoke the invite for ${invite.email}?`,
			message: "Its link stops working. You can send a new invite later.",
			confirmLabel: 'Revoke',
			tone: 'danger',
			action: async () => {
				const response = await platformApi.revokeInvite(invite.id);

				if (response.ok) {
					if (created?.id === invite.id) created = null;
					await invalidate('app:platform-invites');
				}
			}
		});
	}
</script>

<Page width="wide">
	<PageHeader title="Invites" description="Businesses register by invite. Send the owner their link; it works once, for a week." />

	<InviteForm onsubmit={create} />

	{#if created}
		<Card border>
			<div class="flex flex-col gap-4">
				<SectionHeading title={`Invite for ${created.email}`} />

				<Notice tone="warning">Copy this link now and send it to them: it isn't shown again.</Notice>

				<p class="break-all text-sm font-semibold text-(--text)">{created.url}</p>

				<div>
					<Button onclick={copyLink}>Copy link</Button>
				</div>
			</div>
		</Card>
	{/if}

	<SectionHeading title="Waiting to register" />

	<GridTable
		items={data.invites}
		key={(invite) => invite.id}
		columns="minmax(14rem,2fr) 11rem 11rem 9rem"
		headers={['Email', 'Created', 'Expires', '']}
		label="Invites waiting to register"
		empty="No invites waiting."
	>
		{#snippet row(invite)}
			<span class="font-semibold">{invite.email}</span>
			<span class="text-sm">{formatTimestampDDMMYYYY(invite.created_at)}</span>
			<span class="text-sm">{formatTimestampDDMMYYYY(invite.expires_at)}</span>
			<span><Button variant="ghost" onclick={() => revoke(invite)}>Revoke</Button></span>
		{/snippet}
	</GridTable>
</Page>
