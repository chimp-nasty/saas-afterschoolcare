<script lang="ts">
  import type { Snippet } from 'svelte';
  let { title, children, dismissible = true, onclose }:
    { title: string; children: Snippet; dismissible?: boolean; onclose?: () => void } = $props();
  let element: HTMLDialogElement;
  const titleId = $props.id();
  export function open() { if (!element.open) element.showModal(); }
  export function close() { element.close(); }
</script>

<dialog bind:this={element} aria-labelledby={titleId} {onclose}
  oncancel={(event) => { if (!dismissible) event.preventDefault(); }}
  class="m-auto w-[calc(100%-2rem)] max-w-lg rounded border border-(--border) bg-(--surface) p-4 text-(--text)">
  <div class="flex flex-col gap-4">
    <h2 id={titleId} class="text-lg font-semibold">{title}</h2>
    {@render children()}
    <button type="button" disabled={!dismissible} onclick={close} class="min-h-11 self-end px-3">Close</button>
  </div>
</dialog>

<style>dialog::backdrop { background: var(--overlay); }</style>
