<script lang="ts">
	type Props = {
		children?: () => any;
		border?: boolean;
		// Off only for primitives with edge-to-edge content (e.g. DataCard).
		padded?: boolean;
		href?: string;
		onclick?: (event: MouseEvent) => void;
	};

	let {
		children,
		border = false,
		padded = true,
		href,
		onclick
	}: Props = $props();

	const classes = $derived(`
		block w-full min-w-0 rounded-2xl bg-(--surface) wrap-break-word
		${border ? 'border border-(--border) shadow-sm' : ''}
		${padded ? 'p-5' : ''}
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