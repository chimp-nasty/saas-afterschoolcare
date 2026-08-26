<script lang="ts">
	import type { Snippet } from 'svelte';

	let {
		href = '/',
		variant = 'default',
		children
	}: {
		href?: string;
		variant?: 'default' | 'raised' | 'plain';
		children?: Snippet;
	} = $props();

	const variantClass = $derived(
		variant === 'default'
			? 'text-(--hyperlink) hover:text-(--hyperlink-hover) hover:underline'
			: variant === 'raised'
				? 'transition-transform duration-300 hover:scale-110'
				: ''
	);
</script>

<a
	{href}
	class={variantClass}
>
	{@render children?.()}
</a>