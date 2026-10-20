<!--
    A link. Standalone by default ("Back to bookings", "Forgot your
    password?"): 44px tall so it's easy to tap. `inline` for a link inside a
    sentence, which keeps the line height. `external` opens another site
    (e.g. maps) in a new tab.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		href = '/',
		inline = false,
		external = false,
		children
	}: {
		href?: string;
		inline?: boolean;
		external?: boolean;
		children?: Snippet;
	} = $props();
</script>

<a
	{href}
	target={external ? '_blank' : undefined}
	rel={external ? 'noopener noreferrer' : undefined}
	class={[
		'font-semibold text-(--hyperlink) hover:text-(--hyperlink-hover) hover:underline',
		!inline && 'inline-flex min-h-11 items-center'
	]}
>
	{@render children?.()}
</a>
