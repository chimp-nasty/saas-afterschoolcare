<script lang="ts">
  let { message, id }: { message?: string | null; id?: string } = $props();
</script>

{#if message}<p {id} role="alert" class="text-sm text-(--danger)">{message}</p>{/if}
