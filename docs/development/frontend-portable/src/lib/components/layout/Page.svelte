<script lang="ts">
  import type { Snippet } from 'svelte';
  let { children, wide = false }: { children: Snippet; wide?: boolean } = $props();
</script>

<div class={['mx-auto flex w-full min-w-0 flex-col gap-6 p-4', wide ? 'max-w-6xl' : 'max-w-2xl']}>
  {@render children()}
</div>
