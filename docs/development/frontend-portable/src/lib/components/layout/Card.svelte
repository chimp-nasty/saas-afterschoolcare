<script lang="ts">
  import type { Snippet } from 'svelte';
  let { children, padded = true }: { children: Snippet; padded?: boolean } = $props();
</script>

<div class={['min-w-0 rounded border border-(--border) bg-(--surface)', padded && 'p-4']}>
  {@render children()}
</div>
