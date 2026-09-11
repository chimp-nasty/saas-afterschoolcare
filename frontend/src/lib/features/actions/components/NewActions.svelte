<script lang="ts">
    import { onMount } from "svelte";

    import type {
        ActionFilter,
        ActionResponse
    } from "$lib/api/public/types/actions";

    import type {
        Pagination,
        PaginationLoadMode
    } from "$lib/types/pagination";

    import Card from "$lib/components/layout/Card.svelte";
    import DataCard from "$lib/components/layout/DataCard.svelte";

    import PaginationControls from "$lib/components/controls/PaginationControls.svelte";
    import InfiniteScrollTrigger from "$lib/components/controls/InfiniteScrollTrigger.svelte";

    import { buildActionHref } from "$lib/navigation/action-navigation";

    let {
        actions,
        locationCode,
        loader,
        update,
        isLoading = false,
    }: {
        actions: ActionResponse[];
        locationCode: string;
        loader: (
            filters: ActionFilter,
            pagination?: Pagination,
            mode?: PaginationLoadMode
        ) => Promise<number>;
        update: (actionId: string) => Promise<void>;
        isLoading?: boolean;
    } = $props();

    const limit = 10;

    let page = $state(1);
    let hasNext = $state(true);

    let isDesktop = $state(false);
    let viewportReady = $state(false);

    onMount(() => {
        const mediaQuery =
            window.matchMedia("(min-width: 768px)");

        function updateViewport() {
            const wasDesktop = isDesktop;

            isDesktop = mediaQuery.matches;
            viewportReady = true;

            if (
                !wasDesktop &&
                isDesktop &&
                actions.length > limit
            ) {
                void loadPage(
                    page,
                    "replace"
                );
            }
        }

        updateViewport();

        mediaQuery.addEventListener(
            "change",
            updateViewport
        );

        void loadPage(
            1,
            "replace"
        );

        return () => {
            mediaQuery.removeEventListener(
                "change",
                updateViewport
            );
        };
    });

    async function loadPage(
        nextPage: number,
        mode: PaginationLoadMode
    ) {
        const loadedCount = await loader(
            {
                cited: false
            },
            {
                page: nextPage,
                limit
            },
            mode
        );

        page = nextPage;

        hasNext =
            loadedCount === limit;
    }

    async function loadMore() {
        if (
            isLoading ||
            !hasNext
        ) {
            return;
        }

        await loadPage(
            page + 1,
            "append"
        );
    }

    async function handlePrevious() {
        if (
            isLoading ||
            page <= 1
        ) {
            return;
        }

        await loadPage(
            page - 1,
            "replace"
        );

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    async function handleNext() {
        if (
            isLoading ||
            !hasNext
        ) {
            return;
        }

        await loadPage(
            page + 1,
            "replace"
        );

        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    }

    async function handleActionClick(
        actionId: string,
        event: MouseEvent
    ) {
        event.preventDefault();

        const href =
            (event.currentTarget as HTMLAnchorElement).href;

        await update(actionId);

        window.location.href = href;
    }
</script>

<Card>
    <div class="flex flex-col gap-4">
        {#each actions as action}
            <DataCard
                title={action.title}
                href={buildActionHref(
                    locationCode,
                    {
                        childId: action.child_id,
                        target: action.target
                    }
                ) ?? undefined}
                onclick={(event) =>
                    handleActionClick(
                        action.id,
                        event
                    )}
                data={[
                    {
                        label: "Message",
                        value: action.message
                    },
                    {
                        label: "Created",
                        value: action.created_at
                    },
                ]}
            />
        {/each}

        {#if viewportReady}
            {#if isDesktop}
                <PaginationControls
                    {page}
                    {hasNext}
                    {isLoading}
                    onPrevious={handlePrevious}
                    onNext={handleNext}
                />
            {:else}
                <InfiniteScrollTrigger
                    disabled={
                        isLoading ||
                        !hasNext
                    }
                    onTrigger={loadMore}
                />

                {#if isLoading}
                    <div
                        class="
                            py-3 text-center
                            text-sm text-(--text-muted)
                        "
                    >
                        Loading...
                    </div>
                {/if}
            {/if}
        {/if}
    </div>
</Card>