<script lang="ts">
	type Props = {
		children?: () => any;
		border?: boolean;
		href?: string;
		onclick?: (event: MouseEvent) => void;
	};

	let {
		children,
		border = false,
		href,
		onclick
	}: Props = $props();

	const classes = $derived(`
		block w-full min-w-0 rounded-2xl bg-(--surface) wrap-break-word
		${border ? 'border border-(--border) shadow-sm' : ''}
	`);
</script>

{#if href}
	<a
		{href}
		{onclick}
		class={classes}
	>
		{@render children?.()}
	</a>
{:else}
	<div class={classes}>
		{@render children?.()}
	</div>
{/if}