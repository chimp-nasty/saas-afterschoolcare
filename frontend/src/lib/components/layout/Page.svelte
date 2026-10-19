<!--
    The page column: centred, with gap-6 between sections. Customer pages are
    always `narrow` (one column on every screen); `wide` is for admin pages.
-->
<script lang="ts">
    import type { Snippet } from "svelte";

    let {
        width = "narrow",
        children,
    }: {
        width?: "narrow" | "wide";
        children: Snippet;
    } = $props();
</script>

<div
    class={[
        "mx-auto flex w-full flex-col gap-6",
        width === "narrow" ? "max-w-xl" : "max-w-5xl",
    ]}
>
    {@render children()}
</div>
