<!--
    One band of a public site page (docs/public-site.md): full width, with its
    content in the site's column (max-w-6xl). `tone` alternates the
    background between bands; `muted` and `tint` are the app's and the
    business's secondary colour, softened.
-->
<script lang="ts">
    import type { Snippet } from "svelte";

    let {
        id,
        tone = "plain",
        children,
    }: {
        // For in-page links (#centres).
        id?: string;
        tone?: "plain" | "muted" | "tint";
        children: Snippet;
    } = $props();
</script>

<section
    {id}
    class={[
        "w-full scroll-mt-20 px-4 py-10 md:py-16",
        tone === "plain" && "bg-(--surface)",
        tone === "muted" && "bg-(--bg)",
        tone === "tint" && "bg-(--secondary-soft)",
    ]}
>
    <div class="mx-auto flex w-full max-w-6xl flex-col gap-6">
        {@render children()}
    </div>
</section>
