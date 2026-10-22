<!--
    The top of every customer page: an optional eyebrow (e.g. "Step 2 of 3"),
    the title, an optional description, and optional actions beside the title.
-->
<script lang="ts">
    import type { Snippet } from "svelte";

    let {
        title,
        eyebrow,
        description,
        actions,
    }: {
        title: string;
        eyebrow?: string;
        description?: string;
        actions?: Snippet;
    } = $props();
</script>

<header class="flex flex-col gap-1">
    {#if eyebrow}
        <p class="label-text">
            {eyebrow}
        </p>
    {/if}

    <div class="flex items-start justify-between gap-4">
        <h1 class="text-2xl font-extrabold text-(--text)">
            {title}
        </h1>

        {#if actions}
            <div class="shrink-0">
                {@render actions()}
            </div>
        {/if}
    </div>

    {#if description}
        <p class="text-sm text-(--text-muted)">
            {description}
        </p>
    {/if}
</header>
