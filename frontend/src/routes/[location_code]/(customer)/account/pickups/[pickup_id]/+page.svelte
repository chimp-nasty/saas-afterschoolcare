<!--
    Edit or remove a pickup person. Changing the name or phone of someone
    staff have checked or approved means they're checked again; a new email
    gets them a new kiosk PIN. Both ask for confirmation first.
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import Card from "$lib/components/layout/Card.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import { confirmAction } from "$lib/components/overlays/confirm.svelte";
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

    function digits(value: string): string {
        return value.replace(/\D/g, "").replace(/^61/, "0");
    }

    function confirmIdRecheck(changesPhone: boolean): Promise<boolean> {
        const what = changesPhone ? "phone number" : "name";

        return confirmAction({
            title: "Their ID will need checking again",
            message: `Changing ${pickup.first_name}'s ${what} means staff will check their photo ID again at their next pickup.`,
            confirmLabel: "Save changes",
        });
    }

    function confirmNewPin(email: string): Promise<boolean> {
        return confirmAction({
            title: "We'll email a new kiosk PIN",
            message: `${pickup.first_name}'s old PIN will stop working, and a new one will be emailed to ${email}.`,
            confirmLabel: "Save changes",
        });
    }

    // A cancelled save: nothing sent, nothing to show.
    const CANCELLED: ApiResponse = { ok: false, msg: "", data: null, status: 0, fieldErrors: {} };

    async function updatePickup(values: PickupFormValues) {
        const changesName =
            values.first_name.trim() !== pickup.first_name ||
            values.last_name.trim() !== pickup.last_name;
        const changesPhone = digits(values.phone) !== pickup.phone;
        const changesEmail = values.email.trim().toLowerCase() !== pickup.email.toLowerCase();

        if (pickup.staff_approved && (changesName || changesPhone)) {
            if (!(await confirmIdRecheck(changesPhone))) {
                return CANCELLED;
            }
        }

        if (changesEmail && !(await confirmNewPin(values.email.trim()))) {
            return CANCELLED;
        }

        const response = await pickupsApi.update(pickup.id, values);

        if (response.ok && response.data) {
            pickup = response.data;
            await invalidate("app:customer-account");
        }

        return response;
    }

    // --- Removing ----------------------------------------------------------

    async function removePickup() {
        await confirmAction({
            title: `Remove ${pickup.first_name}?`,
            message: `${pickup.first_name} will no longer be able to collect your children or sign in at the kiosk.`,
            confirmLabel: "Remove",
            tone: "danger",
            action: async () => {
                const response = await pickupsApi.deactivate(pickup.id);

                if (response.ok) {
                    await invalidate("app:customer-account");
                    await goto(accountPickupsHref);
                }
            },
        });
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
                : pickup.staff_approved
                    ? "Staff have approved them to collect."
                    : "Staff will check their photo ID the first time they collect."}
            {pickup.kiosk_pin_set
                ? "They've set their own kiosk PIN."
                : pickup.kiosk_pin_issued
                    ? "We've emailed them a kiosk PIN; they'll change it the first time they sign in."
                    : "Their kiosk PIN hasn't been sent yet."}
        </p>
    </Card>

    <PickupForm {pickup} onsubmit={updatePickup} />

    <Button
        variant="ghost"
        fullWidth
        onclick={removePickup}
    >
        Remove pickup person
    </Button>
</Page>
