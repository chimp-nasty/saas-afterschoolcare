<!--
    The booking summary: one section per child, a line per day, and totals.
    Presentational only; the caller supplies the lines and the buttons
    (new booking: Back / Continue, pending review: Cancel / Continue).
-->
<script lang="ts" module>
    export type ReviewLine = {
        date: string;
        serviceName: string;
        priceCents: number;
    };

    export type ReviewChild = {
        childId: string;
        childName: string;
        lines: ReviewLine[];
    };
</script>

<script lang="ts">
    import type { Snippet } from "svelte";

    let {
        serviceName,
        currency,
        children,
        actions,
    }: {
        serviceName: string;
        currency: string;
        children: ReviewChild[];
        actions: Snippet;
    } = $props();

    function formatPrice(priceCents: number): string {
        return new Intl.NumberFormat("en-AU", {
            style: "currency",
            currency,
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
        }).format(priceCents / 100);
    }

    function formatDate(date: string): string {
        return new Intl.DateTimeFormat("en-AU", {
            weekday: "short",
            day: "numeric",
            month: "short",
        }).format(new Date(`${date}T00:00:00`));
    }

    function subtotal(child: ReviewChild): number {
        return child.lines.reduce((total, line) => total + line.priceCents, 0);
    }

    const bookingCount = $derived(
        children.reduce((total, child) => total + child.lines.length, 0)
    );

    const totalPriceCents = $derived(
        children.reduce((total, child) => total + subtotal(child), 0)
    );

    const pricePerSession = $derived(children[0]?.lines[0]?.priceCents);
</script>

<div class="space-y-8">
    <section class="rounded-xl border border-gray-200 bg-white p-6">
        <div class="flex items-start justify-between gap-4">
            <div>
                <h2 class="text-lg font-semibold text-gray-900">
                    {serviceName}
                </h2>

                {#if pricePerSession !== undefined}
                    <p class="mt-1 text-sm text-gray-500">
                        {formatPrice(pricePerSession)}
                        / session
                    </p>
                {/if}
            </div>
        </div>
    </section>

    <div class="space-y-6">
        {#each children as child (child.childId)}
            <section class="rounded-xl border border-gray-200 bg-white">
                <div class="border-b border-gray-200 px-6 py-4">
                    <h3 class="font-semibold text-gray-900">
                        {child.childName}
                    </h3>
                </div>

                <div class="divide-y divide-gray-100">
                    {#each child.lines as line}
                        <div class="flex items-center justify-between px-6 py-4">
                            <div>
                                <p class="font-medium text-gray-900">
                                    {formatDate(line.date)}
                                </p>

                                <p class="mt-1 text-sm text-gray-500">
                                    {line.serviceName}
                                </p>
                            </div>

                            <p class="font-medium text-gray-900">
                                {formatPrice(line.priceCents)}
                            </p>
                        </div>
                    {/each}
                </div>

                <div class="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-6 py-4">
                    <span class="text-sm font-medium text-gray-600">
                        Subtotal
                    </span>

                    <span class="font-semibold text-gray-900">
                        {formatPrice(subtotal(child))}
                    </span>
                </div>
            </section>
        {/each}
    </div>

    <section class="rounded-xl border border-gray-200 bg-white p-6">
        <div class="flex items-center justify-between">
            <div>
                <p class="text-sm text-gray-500">
                    {bookingCount}
                    {bookingCount === 1 ? " booking" : " bookings"}
                </p>

                <p class="mt-1 text-lg font-semibold text-gray-900">
                    Total
                </p>
            </div>

            <p class="text-2xl font-semibold text-gray-900">
                {formatPrice(totalPriceCents)}
            </p>
        </div>
    </section>

    <div class="flex items-center justify-between border-t border-gray-200 pt-6">
        {@render actions()}
    </div>
</div>
