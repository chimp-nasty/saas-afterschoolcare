<script lang="ts">
  import type { Snippet } from 'svelte';
  let { children }: { children: Snippet } = $props();
</script>

<div class="flex flex-col gap-3 sm:flex-row sm:justify-end">{@render children()}</div>
