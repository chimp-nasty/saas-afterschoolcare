<script lang="ts">
  import type { Snippet } from 'svelte';
  import { afterNavigate } from '$app/navigation';
  let { title = 'Navigation', children }: { title?: string; children: Snippet } = $props();
  let element: HTMLDialogElement;
  const titleId = $props.id();
  export function open() { if (!element.open) element.showModal(); }
  export function close() { element.close(); }
  afterNavigate(() => { if (element?.open) close(); });
</script>

<dialog bind:this={element} aria-labelledby={titleId}
  class="fixed inset-y-0 left-0 m-0 h-dvh max-h-none w-80 max-w-[90vw] border-r border-(--border) bg-(--surface) p-4 text-(--text)">
  <div class="flex flex-col gap-4">
    <h2 id={titleId} class="text-lg font-semibold">{title}</h2>
    <button type="button" onclick={close} class="min-h-11 self-end px-3">Close navigation</button>
    {@render children()}
  </div>
</dialog>

<style>dialog::backdrop { background: var(--overlay); }</style>
