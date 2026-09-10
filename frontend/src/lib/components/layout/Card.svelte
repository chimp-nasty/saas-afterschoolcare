<script lang="ts">
	type Props = {
		children?: () => any;
		border?: boolean;
		href?: string;
	};

	let {
		children,
		border = false,
		href
	}: Props = $props();

	const classes = $derived(`
		block
		w-full
		min-w-0
		rounded-2xl
		bg-(--surface)
		wrap-break-word
		${border ? 'border border-(--border) shadow-sm' : ''}
	`);
</script>

{#if href}
	<a
		{href}
		class={classes}
	>
		{@render children?.()}
	</a>
{:else}
	<div class={classes}>
		{@render children?.()}
	</div>
{/if}