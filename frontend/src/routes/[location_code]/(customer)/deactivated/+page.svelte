<!--
    /{location}/deactivated: where a family who deactivated their account
    here is sent from every page (the layout's loader;
    docs/account-deactivation.md). One thing to do: ask the centre to
    reactivate them. The API refuses everything else while they're
    deactivated.
-->
<script lang="ts">
    import { invalidate } from "$app/navigation";

    import ActionBar from "$lib/components/actions/ActionBar.svelte";
    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Notice from "$lib/components/text/Notice.svelte";

    import { createAccountApi } from "$lib/api/auth/adapters/account";
    import { logout } from "$lib/auth/logout";

    let { data } = $props();

    const accountApi = createAccountApi();

    const centre = $derived(data.location.location_name);
    const requested = $derived(data.session?.reactivationRequested ?? false);

    let busy = $state(false);

    async function ask() {
        busy = true;

        try {
            const response = await accountApi.requestReactivation();

            if (response.ok) {
                await invalidate("app:session");
            }
        } finally {
            busy = false;
        }
    }
</script>

<Page>
    <PageHeader
        title="Your account is deactivated"
        description={`You deactivated your account at ${centre}, so you can't book or manage anything here.`}
    />

    <Card border>
        <div class="flex flex-col gap-4">
            <p class="text-base text-(--text)">
                Your details stay with {centre} for as long as the law requires childcare records to be kept,
                then they're securely destroyed.
            </p>

            {#if requested}
                <Notice tone="success">
                    You've asked {centre} to reactivate your account. They'll be in touch.
                </Notice>
            {:else}
                <p class="text-base text-(--text)">
                    Want to come back? Ask {centre} to reactivate your account.
                </p>
            {/if}
        </div>
    </Card>

    <ActionBar>
        <Button variant="ghost" onclick={() => logout(data.locationCode)}>Log out</Button>

        <Button width="w-full md:w-48" isLoading={busy} isDisabled={busy || requested} onclick={ask}>
            {requested ? "Request sent" : "Ask to reactivate"}
        </Button>
    </ActionBar>
</Page>
