<script lang="ts">
  import type { Snippet } from 'svelte';
  let { title, description, actions }:
    { title: string; description?: string; actions?: Snippet } = $props();
</script>

<header class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
  <div><h1 class="text-2xl font-semibold">{title}</h1>
    {#if description}<p class="mt-1 text-(--muted)">{description}</p>{/if}
  </div>
  {@render actions?.()}
</header>
