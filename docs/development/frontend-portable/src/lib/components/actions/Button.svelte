<script lang="ts">
  import type { Snippet } from 'svelte';
  import type { HTMLButtonAttributes } from 'svelte/elements';
  let { children, busy = false, disabled = false, type = 'button', ...rest }:
    HTMLButtonAttributes & { children: Snippet; busy?: boolean } = $props();
</script>

<button {...rest} {type} disabled={disabled || busy} aria-busy={busy}
  class="min-h-11 rounded border border-(--border) bg-(--surface) px-4 py-2 text-(--text) disabled:opacity-50">
  {#if busy}<span role="status">Working…</span>{:else}{@render children()}{/if}
</button>
