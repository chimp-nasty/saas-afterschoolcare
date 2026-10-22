<!--
    An error message: a field's (under the field) or an action's (under the
    form or panel). Nothing renders without a message. The website:
    text-sm; the kiosk: text-lg semibold.
-->
<script lang="ts">
	import type { TextSize } from './textSize';

	let {
		message,
		size = 'web'
	}: {
		message?: string | null;
		size?: TextSize;
	} = $props();
</script>

{#if message}
	<p
		class={['text-(--danger-text)', size === 'kiosk' ? 'text-lg font-semibold' : 'text-sm']}
		role="alert"
	>
		{message}
	</p>
{/if}
