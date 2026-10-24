<!--
    Where the centre is and how to reach it: address (opens maps), phone (tap
    to call, e.g. running late) and email. Used on the landing page, the
    booking review page and Home; with `href`, it's a way into the centre
    (the tenant's page of centres).
-->
<script lang="ts">
    import { goto } from "$app/navigation";

    import Button from "$lib/components/actions/Button.svelte";
    import HyperTextLink from "$lib/components/actions/HyperTextLink.svelte";
    import Card from "$lib/components/layout/Card.svelte";

    import type { PublicLocationResponse } from "$lib/api/schema";
    import { addressLines, mapsUrl } from "../address";

    let {
        location,
        note,
        href,
    }: {
        location: PublicLocationResponse;
        // Optional extra line, e.g. how signing in and out works.
        note?: string;
        // Where "View this centre" goes, when choosing between centres.
        href?: string;
    } = $props();

    const name = $derived(location.location_name);
</script>

<Card border>
    <div class="flex flex-col gap-4">
        <div>
            <p class="label-text">
                Centre
            </p>

            <h2 class="text-lg font-extrabold text-(--text)">
                {name}
            </h2>
        </div>

        <div class="flex flex-col">
            {#each addressLines(location) as line}
                <p class="text-base text-(--text)">{line}</p>
            {/each}

            <div>
                <HyperTextLink href={mapsUrl(location)} external>
                    Open in maps
                </HyperTextLink>
            </div>
        </div>

        {#if location.phone || location.email}
            <div class="flex flex-col">
                {#if location.phone}
                    <div>
                        <HyperTextLink href={`tel:${location.phone.replace(/\s/g, "")}`}>
                            Call {location.phone}
                        </HyperTextLink>
                    </div>
                {/if}

                {#if location.email}
                    <div>
                        <HyperTextLink href={`mailto:${location.email}`}>
                            {location.email}
                        </HyperTextLink>
                    </div>
                {/if}
            </div>
        {/if}

        {#if note}
            <p class="text-sm text-(--text-muted)">
                {note}
            </p>
        {/if}

        {#if href}
            <Button fullWidth onclick={() => goto(href)}>
                View this centre
            </Button>
        {/if}
    </div>
</Card>
