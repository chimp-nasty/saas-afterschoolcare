<!--
    What a list or section says when there's nothing in it ("No bookings
    yet."). The website: secondary text, left-aligned. The kiosk: larger and
    centred, read across the room.
-->
<script lang="ts">
	import type { TextSize } from './textSize';

	let {
		message,
		size = 'web'
	}: {
		message: string;
		size?: TextSize;
	} = $props();
</script>

<p
	class={[
		'text-(--text-muted)',
		size === 'kiosk' ? 'py-4 text-center text-lg' : 'text-sm'
	]}
>
	{message}
</p>
