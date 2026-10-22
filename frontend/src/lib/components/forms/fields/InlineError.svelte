<!--
    A field's error, under the field (Field uses it): the shared ErrorText.
-->
<script lang="ts">
	import ErrorText from '$lib/components/text/ErrorText.svelte';

	let {
		message
	}: {
		message?: string | null;
	} = $props();
</script>

{#if message}
	<div class="mt-1">
		<ErrorText {message} />
	</div>
{/if}
