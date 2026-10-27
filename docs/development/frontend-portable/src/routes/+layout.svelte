<script lang="ts">
  import type { Snippet } from 'svelte';
  import { Toaster } from 'svelte-sonner';
  import './layout.css';
  let { children }: { children: Snippet } = $props();
</script>

<Toaster />
{@render children()}
