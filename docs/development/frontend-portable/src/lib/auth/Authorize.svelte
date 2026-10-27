<script lang="ts">
  import type { Snippet } from 'svelte';
  let { initialized, authenticated, userRoles, roles, permitted = true, children, fallback }:
    { initialized: boolean; authenticated: boolean; userRoles: readonly string[];
      roles?: readonly string[]; permitted?: boolean; children: Snippet; fallback?: Snippet } = $props();
  const allowed = $derived(authenticated && permitted && (!roles || roles.some((role) => userRoles.includes(role))));
</script>

{#if initialized}
  {#if allowed}{@render children()}{:else}{@render fallback?.()}{/if}
{/if}
