<!--
    Admin › Payments: whether this centre can take bookings, from the
    business's own Stripe account (Stripe Connect). Read only: the account
    belongs to the whole business, so its owner manages it in Business
    settings › Payments (/business/payments).
-->
<script lang="ts">
    import { goto } from "$app/navigation";
    import Button from "$lib/components/actions/Button.svelte";
    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import StripeAccountSummary from "$lib/features/payments/components/StripeAccountSummary.svelte";

    import { auth } from "$lib/auth/state.svelte";

    let { data } = $props();

    const isOwner = $derived("tenant_stripe_account" in $auth.tenantPermissions);
</script>

<Page width="wide">
    <PageHeader
        title="Payments"
        description="Families pay your business directly through its own Stripe account. Payouts, refunds you make yourself and disputes are in your Stripe dashboard."
    />

    <Card border>
        <div class="flex flex-col gap-5">
            <StripeAccountSummary account={data.account} />

            {#if isOwner}
                <ActionBar start>
                    <Button variant="ghost" onclick={() => goto("/business/payments")}>Manage in Business settings</Button>
                </ActionBar>
            {:else}
                <p class="text-sm text-(--text-muted)">The business's owner manages this in Business settings.</p>
            {/if}
        </div>
    </Card>
</Page>
