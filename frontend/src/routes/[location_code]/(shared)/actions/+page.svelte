<!--
    Messages from the centre, in the family's account: New (not yet read)
    and Read, newest first, each with its whole text. One about a page in
    their account (e.g. a child's documents) has a button to go there,
    which also marks it read. Lists show 10 at a time ("Show more").
-->
<script lang="ts">
    import { goto, invalidate } from "$app/navigation";
    import { page } from "$app/state";

    import Button from "$lib/components/actions/Button.svelte";
    import TabbedPanels from "$lib/components/controls/TabbedPanels.svelte";
    import Page from "$lib/components/layout/Page.svelte";
    import PageHeader from "$lib/components/layout/PageHeader.svelte";
    import EmptyState from "$lib/components/text/EmptyState.svelte";
    import MessageCard from "$lib/features/actions/components/MessageCard.svelte";

    import { createActionsApi } from "$lib/api/public/adapters/actions";
    import type { ActionResponse } from "$lib/api/schema";
    import { buildActionHref } from "$lib/navigation/action-navigation";
    import { actionTabs } from "$lib/navigation/tabs";
    import { _PAGE_SIZE } from "./+page";

    let { data } = $props();

    const actionsApi = createActionsApi();

    let activeTab = $state<string>(actionTabs.NEW);
    let busyId = $state<string | null>(null);

    const centre = $derived(data.location.location_name);

    const tabs = $derived([
        { id: actionTabs.NEW, label: data.unread.length ? `New (${data.unread.length})` : "New" },
        { id: actionTabs.READ, label: "Read" }
    ]);

    function hrefFor(message: ActionResponse): string | null {
        return buildActionHref(data.locationCode, { childId: message.child_id, target: message.target });
    }

    async function markRead(message: ActionResponse): Promise<boolean> {
        busyId = message.id;

        try {
            return (await actionsApi.updateCitedAt(message.id)).ok;
        } finally {
            busyId = null;
        }
    }

    async function read(message: ActionResponse) {
        if (await markRead(message)) {
            await Promise.all([invalidate("app:actions"), invalidate("app:actions-count")]);
        }
    }

    async function open(message: ActionResponse, href: string) {
        if (!message.cited_at && !(await markRead(message))) return;

        await invalidate("app:actions-count");
        await goto(href);
    }

    // Shows another page of a list (kept in the address).
    function showMore(key: "new_shown" | "read_shown", current: number) {
        const params: Record<string, string> = {
            ...Object.fromEntries(page.url.searchParams),
            [key]: String(current + _PAGE_SIZE),
            state: activeTab
        };

        void goto(`?${new URLSearchParams(params)}`, { keepFocus: true, noScroll: true });
    }
</script>

{#snippet list(messages: ActionResponse[], shown: number, key: "new_shown" | "read_shown", empty: string)}
    {#if !messages.length}
        <EmptyState message={empty} />
    {:else}
        <div class="flex flex-col gap-4">
            {#each messages as message (message.id)}
                <MessageCard
                    {message}
                    href={hrefFor(message)}
                    busy={busyId === message.id}
                    onopen={open}
                    onread={read}
                />
            {/each}

            <!-- A full page means there may be more. -->
            {#if messages.length === shown && shown < 100}
                <Button variant="hyperlink" onclick={() => showMore(key, shown)}>Show more</Button>
            {/if}
        </div>
    {/if}
{/snippet}

<Page>
    <PageHeader title="Messages" description={`From ${centre}.`} />

    <TabbedPanels {tabs} bind:activeTab queryParam="state">
        {#snippet panel(id)}
            {#if id === actionTabs.NEW}
                {@render list(data.unread, data.newShown, "new_shown", "No new messages.")}
            {:else}
                {@render list(data.read, data.readShown, "read_shown", "No read messages yet.")}
            {/if}
        {/snippet}
    </TabbedPanels>
</Page>
