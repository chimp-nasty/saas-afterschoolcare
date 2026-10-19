<!--
    A row of actions: secondary first, main action last. On mobile the
    buttons stack full width with the main action at the bottom (nearest the
    thumb); from md they sit in one row, secondary left and main right.

    `sticky` keeps it at the bottom of the screen on mobile (multi-step
    flows), above the customer BottomNav when there is one.
-->
<script lang="ts" module>
    // Buttons read this to size themselves (see Button.svelte).
    export const ACTION_BAR = Symbol("action-bar");
</script>

<script lang="ts">
    import { setContext, type Snippet } from "svelte";

    let {
        sticky = false,
        children,
    }: {
        sticky?: boolean;
        children: Snippet;
    } = $props();

    setContext(ACTION_BAR, true);
</script>

<div
    class={[
        "flex flex-col gap-3 md:flex-row md:items-center md:justify-between",
        sticky && [
            "sticky bottom-(--bottom-nav-height) z-30 -mx-4 border-t border-(--border) bg-(--surface)/95 px-4 py-3 backdrop-blur-md",
            "md:static md:mx-0 md:border-0 md:bg-transparent md:p-0 md:backdrop-blur-none",
        ],
    ]}
>
    {@render children()}
</div>
