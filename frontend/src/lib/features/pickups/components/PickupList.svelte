<!--
    Account → Pickups: the account holder (from their profile, not tappable)
    and the people they've added (tap to edit), then "Add a pickup person"
    until the limit.
-->
<script lang="ts">
    import { goto } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";

    import type { PickupResponse } from "$lib/api/schema";
    import { formatPhone } from "$lib/utils/helpers";
    import { PICKUP_LIMIT, relationLabel } from "../types";

    let {
        pickups,
        locationCode,
    }: {
        pickups: PickupResponse[];
        locationCode: string;
    } = $props();

    const addedCount = $derived(
        pickups.filter((pickup) => !pickup.is_account_holder).length
    );
</script>

<div class="flex flex-col gap-4">
    <p class="text-sm text-(--text-muted)">
        Everyone here can collect all of your children. Staff check each
        person's photo ID the first time they collect.
    </p>

    {#each pickups as pickup (pickup.id)}
        <DataCard
            title={pickup.is_account_holder
                ? `${pickup.first_name} ${pickup.last_name} (you)`
                : `${pickup.first_name} ${pickup.last_name}`}
            href={pickup.is_account_holder
                ? undefined
                : `/${locationCode}/account/pickups/${pickup.id}`}
            data={[
                { label: "Relationship", value: relationLabel(pickup) },
                { label: "Phone", value: formatPhone(pickup.phone) },
                { label: "ID check", value: pickup.identity_verified ? "Checked" : "Not yet checked" },
            ]}
        />
    {:else}
        <p class="text-sm text-(--text-muted)">
            Add your phone number in Profile to appear on your pickup list.
        </p>
    {/each}

    {#if addedCount < PICKUP_LIMIT}
        <Button
            fullWidth
            onclick={() => goto(`/${locationCode}/account/pickups/new`)}
        >
            Add a pickup person
        </Button>
    {:else}
        <p class="text-sm text-(--text-muted)">
            You can have up to {PICKUP_LIMIT} pickup people. Remove one to add
            someone else.
        </p>
    {/if}
</div>
