<script lang="ts">
	let {
		message
	}: {
		message?: string | null;
	} = $props();
</script>

{#if message}
	<p class="mt-1 text-sm text-(--danger-text)">
		{message}
	</p>
{/if}