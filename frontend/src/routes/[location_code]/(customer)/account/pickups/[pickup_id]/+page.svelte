<!--
    Edit or remove a pickup person. Changing the name or phone of someone
    whose ID staff have checked means they're checked again (and a new phone
    also resets their kiosk PIN), so that asks for confirmation first.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";
    import PickupForm, { type PickupFormValues } from "$lib/features/pickups/components/PickupForm.svelte";

    import { createPickupsApi } from "$lib/api/public/adapters/pickups";
    import type { ApiResponse } from "$lib/api/wrapper";
    import type { PickupResponse } from "$lib/api/schema";
    import { relationLabel } from "$lib/features/pickups/types";
    import { accountTabs } from "$lib/navigation/tabs";

    let { data } = $props();

    const pickupsApi = createPickupsApi();

    // Starts from the loader; a save replaces it with what the server
    // returns (including an ID check or PIN it may have reset).
    let pickup = $derived<PickupResponse>(data.pickup);

    const accountPickupsHref = $derived(
        `/${data.locationCode}/account?state=${accountTabs.PICKUPS}`
    );

    // --- Confirming an ID re-check ------------------------------------------

    let resetModal: Modal;
    let resolveReset: ((confirmed: boolean) => void) | null = null;
    let resetChangesPhone = $state(false);

    function digits(value: string): string {
        return value.replace(/\D/g, "").replace(/^61/, "0");
    }

    function askToConfirmReset(changesPhone: boolean): Promise<boolean> {
        resetChangesPhone = changesPhone;
        resetModal.open();

        return new Promise((resolve) => {
            resolveReset = resolve;
        });
    }

    function answerReset(confirmed: boolean) {
        resolveReset?.(confirmed);
        resolveReset = null;
        resetModal.close();
    }

    // A cancelled save: nothing sent, nothing to show.
    const CANCELLED: ApiResponse = { ok: false, msg: "", data: null, status: 0, fieldErrors: {} };

    async function updatePickup(values: PickupFormValues) {
        const changesName =
            values.first_name.trim() !== pickup.first_name ||
            values.last_name.trim() !== pickup.last_name;
        const changesPhone = digits(values.phone) !== pickup.phone;

        if (pickup.identity_verified && (changesName || changesPhone)) {
            if (!(await askToConfirmReset(changesPhone))) {
                return CANCELLED;
            }
        }

        const response = await pickupsApi.update(pickup.id, values);

        if (response.ok && response.data) {
            pickup = response.data;
            await invalidate("app:customer-account");
        }

        return response;
    }

    // --- Removing ----------------------------------------------------------

    let removeModal: Modal;
    let isRemoving = $state(false);

    async function removePickup() {
        isRemoving = true;

        try {
            const response = await pickupsApi.deactivate(pickup.id);

            if (response.ok) {
                await invalidate("app:customer-account");
                await goto(accountPickupsHref);
                return;
            }

            removeModal.close();
        } finally {
            isRemoving = false;
        }
    }
</script>

<Page>
    <PageHeader
        title={`${pickup.first_name} ${pickup.last_name}`}
        description={relationLabel(pickup)}
    />

    <Card border>
        <p class="text-sm text-(--text-muted)">
            {pickup.identity_verified
                ? "Staff have checked their photo ID."
                : "Staff will check their photo ID the first time they collect."}
            {pickup.kiosk_pin_set
                ? "They've set their own kiosk PIN."
                : "Their kiosk PIN is 1111 until they choose their own at the centre."}
        </p>
    </Card>

    <PickupForm {pickup} onsubmit={updatePickup} />

    <Button
        variant="ghost"
        fullWidth
        onclick={() => removeModal.open()}
    >
        Remove pickup person
    </Button>
</Page>

<Modal
    bind:this={resetModal}
    title="Their ID will need checking again"
    onclose={() => resolveReset && answerReset(false)}
>
    <p class="text-sm text-(--text-muted)">
        Changing {pickup.first_name}'s
        {resetChangesPhone ? "phone number" : "name"} means staff will check
        their photo ID again at their next pickup.
        {#if resetChangesPhone}
            Their kiosk PIN will also go back to 1111, and they'll choose a new
            one when they next sign in.
        {/if}
    </p>

    {#snippet actions()}
        <Button variant="ghost" onclick={() => answerReset(false)}>
            Cancel
        </Button>

        <Button onclick={() => answerReset(true)}>
            Save changes
        </Button>
    {/snippet}
</Modal>

<Modal bind:this={removeModal} title={`Remove ${pickup.first_name}?`}>
    <p class="text-sm text-(--text-muted)">
        {pickup.first_name} will no longer be able to collect your children or
        sign in at the kiosk.
    </p>

    {#snippet actions()}
        <Button variant="ghost" onclick={() => removeModal.close()}>
            Keep
        </Button>

        <Button onclick={removePickup} isLoading={isRemoving}>
            Remove
        </Button>
    {/snippet}
</Modal>
