<!--
    The customer's navigation on mobile: fixed to the bottom of the screen,
    one link per item. Hidden from md, where the sidebar takes over.
-->
<script lang="ts" module>
    import type { Icon } from "lucide-svelte";

    export type BottomNavItem = {
        label: string;
        href: string;
        icon: typeof Icon;
        isActive: boolean;
    };
</script>

<script lang="ts">
    let {
        items,
    }: {
        items: BottomNavItem[];
    } = $props();
</script>

<nav
    class="fixed inset-x-0 bottom-0 z-40 border-t border-(--border) bg-(--surface)/95 pb-[env(safe-area-inset-bottom)] backdrop-blur-md md:hidden"
>
    <ul
        class="grid"
        style:grid-template-columns={`repeat(${items.length}, minmax(0, 1fr))`}
    >
        {#each items as item (item.href)}
            <li>
                <a
                    href={item.href}
                    aria-current={item.isActive ? "page" : undefined}
                    class={[
                        "flex h-16 flex-col items-center justify-center gap-1 text-xs font-extrabold uppercase tracking-wide",
                        item.isActive ? "text-(--primary)" : "text-(--text-muted)",
                    ]}
                >
                    <item.icon size={20} />
                    {item.label}
                </a>
            </li>
        {/each}
    </ul>
</nav>
