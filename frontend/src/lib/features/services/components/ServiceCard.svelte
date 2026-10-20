<!--
    Everything a family should know about a service before booking: times,
    ages, price, what it is, and its refund and late-pickup policies. Used on
    the public landing page.
-->
<script lang="ts">
    import Card from "$lib/components/layout/Card.svelte";

    import type { LocationServiceSelectionResponse } from "$lib/api/schema";
    import { formatMoney, formatTimeRange } from "$lib/utils/helpers";
    import { agesLabel, latePolicy, refundPolicy } from "../policies";

    let {
        service,
    }: {
        service: LocationServiceSelectionResponse;
    } = $props();

    const late = $derived(latePolicy(service));
</script>

<Card border>
    <div class="flex flex-col gap-3">
        <div class="flex items-start justify-between gap-4">
            <div>
                <h3 class="text-lg font-extrabold text-(--text)">
                    {service.service_name}
                </h3>

                <p class="text-sm text-(--text-muted)">
                    {formatTimeRange(service.start_time, service.end_time)} · {agesLabel(service)}
                </p>
            </div>

            <p class="shrink-0 text-right">
                <span class="block text-base font-semibold text-(--text)">
                    {formatMoney(service.current_price_cents, service.currency)}
                </span>

                <span class="text-sm text-(--text-muted)">
                    / session
                </span>
            </p>
        </div>

        {#if service.description}
            <p class="text-base text-(--text)">
                {service.description}
            </p>
        {/if}

        <ul class="flex flex-col gap-1 text-sm text-(--text-muted)">
            <li>{refundPolicy(service.refund_cutoff_days)}</li>

            {#if late}
                <li>{late}</li>
            {/if}
        </ul>
    </div>
</Card>
