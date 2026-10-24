<!--
    Business settings › Payments: the business's own Stripe account (Stripe
    Connect). Families pay the business directly; it owns payouts, refunds
    and disputes in its Stripe dashboard. The owner connects the account,
    linking the one the business already has ("Connect with Stripe") or
    making a new one (Stripe's hosted onboarding); both return here. They
    also refresh its status and turn online payments off or on. Turning them
    off stops new bookings at every centre; past payments can still be
    refunded.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";
    import { page } from "$app/state";
    import { onMount } from "svelte";
    import { toast } from "svelte-sonner";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
    import StripeAccountSummary from "$lib/features/payments/components/StripeAccountSummary.svelte";

    import { createStripeAccountApi } from "$lib/api/tenancy/adapters/stripeAccount";

    let { data } = $props();

    const stripeApi = createStripeAccountApi();

    const account = $derived(data.account);

    let isBusy = $state(false);

    async function run(action: () => Promise<unknown>) {
        isBusy = true;

        try {
            await action();
            await invalidate("app:stripe-account");
        } finally {
            isBusy = false;
        }
    }

    // Off to Stripe (linking an existing account, or onboarding a new
    // one); it sends them back here.
    async function connect(existing = false) {
        isBusy = true;

        try {
            const response = existing ? await stripeApi.linkExisting() : await stripeApi.onboarding();

            if (response.ok && response.data) {
                window.location.href = response.data.url;
                return;
            }
        } finally {
            isBusy = false;
        }
    }

    async function turnOff() {
        await confirmAction({
            title: "Turn off online payments?",
            message: "Families won't be able to book at any of your centres until you turn them back on. Existing bookings stay, and past payments can still be refunded.",
            confirmLabel: "Turn off",
            tone: "danger",
            action: async () => {
                await stripeApi.disconnect();
                await invalidate("app:stripe-account");
            },
        });
    }

    // How linking an existing account went (the API's OAuth callback).
    const LINK_RESULTS: Record<string, () => void> = {
        connected: () => toast.success("Your Stripe account is connected."),
        cancelled: () => toast.info("Stripe wasn't connected."),
        taken: () => toast.error("That Stripe account is already connected to another business."),
        error: () => toast.error("Stripe couldn't be connected. Please try again.")
    };

    // Back from Stripe: "return" means check the status now; "refresh"
    // means the onboarding link expired, so start a new one; the rest are
    // how linking an existing account went.
    onMount(() => {
        const from = page.url.searchParams.get("stripe");

        if (!from) return;

        void goto(page.url.pathname, { replaceState: true, noScroll: true });

        if (from === "refresh") {
            void connect();
        } else if (from in LINK_RESULTS) {
            LINK_RESULTS[from]();
        } else if (account?.connected) {
            void run(() => stripeApi.refresh());
        }
    });
</script>

<Page width="wide">
    <PageHeader
        title="Payments"
        description="Families pay your business directly through your own Stripe account, at every centre. Payouts, refunds you make yourself and disputes are in your Stripe dashboard."
    />

    <Card border>
        <div class="flex flex-col gap-5">
            <StripeAccountSummary {account} />

            <ActionBar>
                {#if account?.connected && !account.revoked}
                    <Button variant="ghost" isLoading={isBusy} onclick={() => run(() => stripeApi.refresh())}>Refresh status</Button>
                {/if}

                {#if !account?.connected || account.revoked}
                    {#if account?.can_link_existing}
                        <Button variant="ghost" isLoading={isBusy} onclick={() => connect()}>Create a new Stripe account</Button>
                        <Button isLoading={isBusy} onclick={() => connect(true)}>Connect your Stripe account</Button>
                    {:else}
                        <Button isLoading={isBusy} onclick={() => connect()}>Connect Stripe</Button>
                    {/if}
                {:else if (!account.details_submitted || !account.charges_enabled) && !account.is_linked}
                    <Button isLoading={isBusy} onclick={() => connect()}>Continue setup</Button>
                {:else if !account.details_submitted || !account.charges_enabled}
                    <!-- A linked account is finished in its own Stripe dashboard. -->
                {:else if account.disconnected}
                    <Button isLoading={isBusy} onclick={() => run(() => stripeApi.reconnect())}>Turn on online payments</Button>
                {:else}
                    <Button variant="ghost" onclick={turnOff}>Turn off online payments</Button>
                {/if}

                <!-- Swap to the business's own existing account. -->
                {#if account?.connected && !account.revoked && account.can_link_existing}
                    <Button variant="ghost" isLoading={isBusy} onclick={() => connect(true)}>Use a different Stripe account</Button>
                {/if}
            </ActionBar>
        </div>
    </Card>

    {#if account?.connected}
        <HyperTextLink href="https://dashboard.stripe.com/" external>Open your Stripe dashboard</HyperTextLink>
    {/if}
</Page>
