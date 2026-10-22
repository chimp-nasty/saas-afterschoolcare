<!--
    Admin › Payments: the business's own Stripe account (Stripe Connect).
    Families pay the business directly; it owns payouts, refunds and
    disputes in its Stripe dashboard. Everyone here sees whether bookings
    are open; superadmins connect the account, linking the one the
    business already has ("Connect with Stripe") or making a new one
    (Stripe's hosted onboarding); both return here. They also refresh its
    status and turn online payments off or on. Turning them off stops new bookings; past payments can still be
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
    import LabelValueList from "$lib/components/text/LabelValueList.svelte";
    import Notice from "$lib/components/text/Notice.svelte";
    import type { Tone } from "$lib/components/text/textSize";

    import { auth } from "$lib/auth/state.svelte";
    import { createStripeAccountApi } from "$lib/api/tenancy/adapters/stripeAccount";
    import { formatTimestamp } from "$lib/utils/helpers";

    let { data } = $props();

    const stripeApi = createStripeAccountApi();

    const isSuperadmin = $derived($auth.roles.includes("superadmin"));
    const account = $derived(data.account);

    let isBusy = $state(false);

    // How things stand, in one line.
    const standing = $derived.by((): { tone: Tone; text: string } => {
        if (!account?.connected) {
            return { tone: "warning", text: "Stripe isn't connected. Families can't book until it is." };
        }

        if (account.revoked) {
            return { tone: "danger", text: "This Stripe account no longer gives us access. Connect Stripe again to take bookings; refund past payments in your Stripe dashboard." };
        }

        if (account.disconnected) {
            return { tone: "warning", text: "Online payments are turned off, so families can't book. Past payments can still be refunded." };
        }

        if (!account.takes_payments && account.is_linked) {
            return { tone: "warning", text: "Your Stripe account isn't ready to take payments yet. Finish setting it up in your Stripe dashboard, then refresh the status here." };
        }

        if (!account.takes_payments) {
            return { tone: "warning", text: "Stripe setup isn't finished. Families can book once Stripe has everything it needs." };
        }

        return { tone: "success", text: "Taking bookings. Families pay into your Stripe account." };
    });

    const onOff = (value: boolean | undefined) => (value ? "On" : "Off");

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
            message: "Families won't be able to book until you turn them back on. Existing bookings stay, and past payments can still be refunded.",
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

        if (!from || !isSuperadmin) return;

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
        description="Families pay your business directly through your own Stripe account. Payouts, refunds you make yourself and disputes are in your Stripe dashboard."
    />

    <Card border>
        <div class="flex flex-col gap-5">
            <Notice tone={standing.tone}>{standing.text}</Notice>

            {#if account?.connected}
                <LabelValueList
                    columns={3}
                    items={[
                        { label: "Setup", value: account.details_submitted ? "Finished" : "Not finished" },
                        { label: "Card payments", value: onOff(account.charges_enabled) },
                        { label: "Payouts", value: onOff(account.payouts_enabled) },
                        { label: "Online payments here", value: account.disconnected ? "Turned off" : "Turned on" },
                        { label: "Connected", value: account.connected_at ? formatTimestamp(account.connected_at) : null },
                        { label: "Stripe account", value: account.stripe_account_id }
                    ]}
                />
            {/if}

            {#if isSuperadmin}
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
            {:else}
                <p class="text-sm text-(--text-muted)">Only a superadmin can change this.</p>
            {/if}
        </div>
    </Card>

    {#if account?.connected}
        <HyperTextLink href="https://dashboard.stripe.com/" external>Open your Stripe dashboard</HyperTextLink>
    {/if}
</Page>
