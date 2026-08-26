<script lang="ts">
	type Props = {
		children?: () => any;
		border?: boolean;
	};

	let {
		children,
		border = false
	}: Props = $props();
</script>

<div
	class={`
		w-full
		min-w-0
		rounded-2xl
		bg-(--surface)
		wrap-break-word
		${border ? 'border border-(--border) shadow-sm' : ''}
	`}
>
	{@render children?.()}
</div>