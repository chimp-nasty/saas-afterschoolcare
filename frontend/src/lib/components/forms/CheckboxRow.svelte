<!--
    A checkbox with a title and an optional help line, both in normal case:
    the whole row is the tap target (48px). Title is body semibold; help is
    secondary text.
-->
<script lang="ts">
	let {
		checked = $bindable(false),
		title,
		help,
		disabled = false,
		onchange
	}: {
		checked?: boolean;
		title: string;
		help?: string | null;
		disabled?: boolean;
		onchange?: (checked: boolean) => void;
	} = $props();
</script>

<label class="flex min-h-12 items-start gap-3 py-1">
	<input
		type="checkbox"
		class="mt-1 size-5 shrink-0"
		bind:checked
		{disabled}
		onchange={(event) => onchange?.(event.currentTarget.checked)}
	/>
	<span class="flex flex-col gap-0.5">
		<span class="text-base font-semibold text-(--text)">{title}</span>
		{#if help}
			<span class="text-sm text-(--text-muted)">{help}</span>
		{/if}
	</span>
</label>
