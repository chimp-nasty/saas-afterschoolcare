<!--
    The booking summary: one section per child, a line per day, and totals.
    Presentational only; the caller supplies the lines, optional per-line
    actions (review: refund a day), and its own ActionBar below.
-->
<script lang="ts" module>
    export type ReviewLine = {
        // Set once the booking exists (review screen); lets lineActions find it.
        bookingId?: string;
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

    import Card from "$lib/components/layout/Card.svelte";

    import { formatDate, formatMoney } from "$lib/utils/helpers";

    let {
        serviceName,
        currency,
        children,
        lineActions,
    }: {
        serviceName: string;
        currency: string;
        children: ReviewChild[];
        lineActions?: Snippet<[ReviewLine]>;
    } = $props();

    function formatPrice(priceCents: number): string {
        return formatMoney(priceCents, currency);
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

<div class="flex flex-col gap-4">
    <Card border>
        <h2 class="text-lg font-extrabold text-(--text)">
            {serviceName}
        </h2>

        {#if pricePerSession !== undefined}
            <p class="text-sm text-(--text-muted)">
                {formatPrice(pricePerSession)} / session
            </p>
        {/if}
    </Card>

    <!-- Unpadded: the rows and subtotal run edge to edge. -->
    {#each children as child (child.childId)}
        <Card border padded={false}>
            <h3 class="border-b border-(--border) px-5 py-4 text-xs font-extrabold uppercase tracking-wide text-(--text-muted)">
                {child.childName}
            </h3>

            <div class="divide-y divide-(--border)">
                {#each child.lines as line (line.bookingId ?? line.date)}
                    <div class="flex items-start justify-between gap-4 px-5 py-4">
                        <div>
                            <p class="font-semibold text-(--text)">
                                {formatDate(line.date)}
                            </p>

                            <p class="text-sm text-(--text-muted)">
                                {line.serviceName}
                            </p>
                        </div>

                        <div class="flex flex-col items-end gap-2">
                            <p class="font-semibold text-(--text)">
                                {formatPrice(line.priceCents)}
                            </p>

                            {@render lineActions?.(line)}
                        </div>
                    </div>
                {/each}
            </div>

            <div class="flex items-center justify-between rounded-b-2xl border-t border-(--border) bg-(--surface-muted) px-5 py-4">
                <span class="text-sm text-(--text-muted)">
                    Subtotal
                </span>

                <span class="font-semibold text-(--text)">
                    {formatPrice(subtotal(child))}
                </span>
            </div>
        </Card>
    {/each}

    <Card border>
        <div class="flex items-center justify-between gap-4">
            <div>
                <p class="text-sm text-(--text-muted)">
                    {bookingCount} {bookingCount === 1 ? "session" : "sessions"}
                </p>

                <p class="text-lg font-extrabold text-(--text)">
                    Total
                </p>
            </div>

            <p class="text-2xl font-extrabold text-(--text)">
                {formatPrice(totalPriceCents)}
            </p>
        </div>
    </Card>
</div>
