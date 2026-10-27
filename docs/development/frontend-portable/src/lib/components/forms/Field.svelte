<script lang="ts">
  import type { Snippet } from 'svelte';
  import ErrorText from '$lib/components/text/ErrorText.svelte';
  let { label, error, children }:
    { label: string; error?: string | null;
      children: Snippet<[{ id: string; 'aria-describedby': string | undefined; 'aria-invalid': boolean }]> } = $props();
  const id = $props.id();
</script>

<div class="flex flex-col gap-1">
  <label for={id}>{label}</label>
  {@render children({ id, 'aria-describedby': error ? `${id}-error` : undefined, 'aria-invalid': !!error })}
  <ErrorText message={error} id={`${id}-error`} />
</div>
