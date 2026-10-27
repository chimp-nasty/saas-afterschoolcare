<script lang="ts">
  import type { Snippet } from 'svelte';
  import Button from '$lib/components/actions/Button.svelte';
  let { children, onsubmit, busy = false, submitLabel = 'Save' }:
    { children: Snippet; onsubmit: () => void | Promise<void>; busy?: boolean; submitLabel?: string } = $props();
</script>

<form class="flex flex-col gap-4" aria-busy={busy}
  onsubmit={(event) => { event.preventDefault(); if (!busy) void onsubmit(); }}>
  {@render children()}
  <Button type="submit" {busy}>{submitLabel}</Button>
</form>
