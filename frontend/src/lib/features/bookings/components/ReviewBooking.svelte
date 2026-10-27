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
        // "3:00pm – 6:00pm"
        time?: string;
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
    import SectionHeading from "$lib/components/text/SectionHeading.svelte";

    import { formatDate, formatMoney } from "$lib/utils/helpers";

    let {
        serviceName,
        currency,
        children,
        refundedCents = 0,
        lineActions,
    }: {
        serviceName: string;
        currency: string;
        children: ReviewChild[];
        // Review screen: what's been refunded of what was paid.
        refundedCents?: number;
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
        <SectionHeading
            title={serviceName}
            description={pricePerSession !== undefined
                ? `${formatPrice(pricePerSession)} / session`
                : null}
        />
    </Card>

    <!-- Unpadded: the rows and subtotal run edge to edge. -->
    {#each children as child (child.childId)}
        <Card border padded={false}>
            <!-- A compact data card's title: the label role, as TitleCard. -->
            <h3 class="border-b border-(--border) px-5 py-4 label-text">
                {child.childName}
            </h3>

            <div class="divide-y divide-(--border)">
                {#each child.lines as line (line.bookingId ?? line.date)}
                    <div class="flex flex-col gap-3 px-5 py-4">
                        <div class="flex items-start justify-between gap-4">
                            <div>
                                <p class="text-base font-semibold text-(--text)">
                                    {formatDate(line.date)}
                                </p>

                                <p class="text-sm text-(--text-muted)">
                                    {line.serviceName}{line.time ? ` · ${line.time}` : ""}
                                </p>
                            </div>

                            <p class="text-base font-semibold text-(--text)">
                                {formatPrice(line.priceCents)}
                            </p>
                        </div>

                        <!-- The line's action and where it stands, on the left
                             under the date (hidden when there's neither). -->
                        {#if lineActions}
                            <div class="flex items-center gap-3 empty:hidden">
                                {@render lineActions(line)}
                            </div>
                        {/if}
                    </div>
                {/each}
            </div>

            <div class="flex items-center justify-between rounded-b-2xl border-t border-(--border) bg-(--surface-muted) px-5 py-4">
                <span class="label-text">
                    Subtotal
                </span>

                <span class="text-base font-semibold text-(--text)">
                    {formatPrice(subtotal(child))}
                </span>
            </div>
        </Card>
    {/each}

    <Card border>
        <div class="flex items-center justify-between gap-4">
            <div>
                <p class="label-text">
                    {refundedCents > 0 ? "Total paid" : "Total"}
                </p>

                <p class="text-sm text-(--text-muted)">
                    {bookingCount} {bookingCount === 1 ? "session" : "sessions"}
                </p>
            </div>

            <p class="text-2xl font-extrabold text-(--text)">
                {formatPrice(totalPriceCents)}
            </p>
        </div>

        {#if refundedCents > 0}
            <div class="mt-4 flex items-center justify-between gap-4 border-t border-(--border) pt-4">
                <span class="label-text">
                    Refunded
                </span>

                <span class="text-base font-semibold text-(--text)">
                    −{formatPrice(refundedCents)}
                </span>
            </div>
        {/if}
    </Card>
</div>
