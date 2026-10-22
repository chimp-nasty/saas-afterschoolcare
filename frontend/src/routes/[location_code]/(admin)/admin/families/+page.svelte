<!--
    Admin › Families: find a family at this centre by a child's or parent's
    name, an email or a phone number, and open its page.
-->
<script lang="ts">
    import { goto } from "$app/navigation";
    import { untrack } from "svelte";

    import Button from "$lib/components/actions/Button.svelte";
    import GridTable from "$lib/components/layout/GridTable.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";

    import { formatPhone } from "$lib/utils/helpers";

    let { data } = $props();

    // Starts as what was searched (the page reloads with each search).
    let text = $state(untrack(() => data.q));

    function search(event: SubmitEvent) {
        event.preventDefault();

        if (text.trim().length >= 2) {
            void goto(`?q=${encodeURIComponent(text.trim())}`, { keepFocus: true });
        }
    }
</script>

<Page width="wide">
    <PageHeader title="Families" description="Find a family at this centre to see their children, bookings, attendance and payments." />

    <form class="flex flex-wrap items-end gap-3" onsubmit={search}>
        <label class="flex min-w-72 flex-1 flex-col gap-1">
            <span class="label-text">Child or parent name, email or phone</span>
            <input type="search" minlength="2" autocomplete="off" bind:value={text} />
        </label>
        <Button type="submit" isDisabled={text.trim().length < 2}>Search</Button>
    </form>

    {#if data.families}
        <GridTable
            items={data.families}
            key={(family) => family.user_id}
            columns="minmax(10rem,1.4fr) minmax(10rem,1.4fr) minmax(8rem,1fr) 6rem 6rem"
            headers={["Family", "Children", "Phone", "Upcoming", "Unpaid"]}
            label="Families"
            minWidth="44rem"
            empty={`No families match "${data.q}".`}
            onrowclick={(family) => goto(`/${data.locationCode}/admin/families/${family.user_id}`)}
        >
            {#snippet row(family)}
                <span class="text-base font-semibold text-(--text)" role="cell">{family.first_name} {family.last_name}</span>
                <span class="text-base text-(--text)" role="cell">{family.children ?? "—"}</span>
                <span class="text-base text-(--text)" role="cell">{family.phone ? formatPhone(family.phone) : "—"}</span>
                <span class="text-base text-(--text)" role="cell">{family.upcoming}</span>
                <span class={["text-base", family.unpaid ? "font-semibold text-(--warning-text)" : "text-(--text-muted)"]} role="cell">
                    {family.unpaid ? `${family.unpaid} ⚠` : "—"}
                </span>
            {/snippet}
        </GridTable>
    {/if}
</Page>
