<!--
    A labelled multi-select: a trigger styled like the other underline inputs,
    opening a list of 44px checkbox rows (with "Select all"). Tapping outside
    or Escape closes it.
-->
<script lang="ts" module>
	export type MultiSelectOption = {
		value: string;
		label: string;
		disabled?: boolean;
	};
</script>

<script lang="ts">
	import { onMount } from 'svelte';
	import { ChevronDown } from 'lucide-svelte';

	import Field from '../Field.svelte';

	type Props = {
		value: string[];
		label: string;
		options: MultiSelectOption[];

		placeholder?: string;

		isDisabled?: boolean;

		error?: string | null;
	};

	let {
		value = $bindable([]),
		label,
		options,

		placeholder = 'Select options',

		isDisabled = false,

		error
	}: Props = $props();

	let containerElement: HTMLDivElement;
	let isOpen = $state(false);

	const selectableOptions = $derived(
		options.filter((option) => !option.disabled)
	);

	const selectedCount = $derived(
		selectableOptions.filter((option) =>
			value.includes(option.value)
		).length
	);

	const allSelected = $derived(
		selectableOptions.length > 0 &&
		selectedCount === selectableOptions.length
	);

	const triggerText = $derived.by(() => {
		if (selectedCount === 0) {
			return placeholder;
		}

		if (selectedCount === 1) {
			return (
				options.find((option) =>
					value.includes(option.value)
				)?.label ?? placeholder
			);
		}

		return `${selectedCount} selected`;
	});

	function toggleOption(optionValue: string) {
		value = value.includes(optionValue)
			? value.filter((item) => item !== optionValue)
			: [...value, optionValue];
	}

	function toggleAll() {
		value = allSelected
			? []
			: selectableOptions.map((option) => option.value);
	}

	onMount(() => {
		// pointerdown, not mousedown, so taps on phones close it too.
		function handlePointerDown(event: PointerEvent) {
			if (
				containerElement &&
				!containerElement.contains(event.target as Node)
			) {
				isOpen = false;
			}
		}

		function handleKeyDown(event: KeyboardEvent) {
			if (event.key === 'Escape') {
				isOpen = false;
			}
		}

		document.addEventListener('pointerdown', handlePointerDown);
		document.addEventListener('keydown', handleKeyDown);

		return () => {
			document.removeEventListener('pointerdown', handlePointerDown);
			document.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

{#snippet optionRow(checked: boolean, text: string, disabled: boolean, onclick: () => void, role?: string)}
	<button
		type="button"
		{role}
		aria-selected={role ? checked : undefined}
		{disabled}
		{onclick}
		class="flex min-h-11 w-full items-center gap-3 rounded-lg px-3 text-left text-base text-(--text) hover:bg-(--surface-muted) disabled:cursor-not-allowed disabled:opacity-50"
	>
		<input
			type="checkbox"
			{checked}
			{disabled}
			tabindex="-1"
			aria-hidden="true"
			class="rounded text-(--primary)"
		/>

		{text}
	</button>
{/snippet}

<div
	class="relative"
	bind:this={containerElement}
>
	<Field {label} {error}>
		{#snippet children(id)}
			<button
				{id}
				type="button"
				disabled={isDisabled}
				aria-expanded={isOpen}
				aria-haspopup="listbox"
				onclick={() => (isOpen = !isOpen)}
				class={[
					'flex min-h-11 w-full items-center justify-between gap-2 border-b border-(--border) text-left text-base disabled:cursor-not-allowed disabled:opacity-65',
					isOpen && 'border-(--primary)',
					selectedCount === 0 ? 'text-(--text-muted)' : 'text-(--text)'
				]}
			>
				{triggerText}

				<ChevronDown size={18} class="shrink-0 text-(--text-muted)" />
			</button>
		{/snippet}
	</Field>

	{#if isOpen}
		<div
			role="listbox"
			aria-multiselectable="true"
			class="absolute inset-x-0 z-50 mt-1 flex max-h-72 flex-col overflow-y-auto rounded-2xl border border-(--border) bg-(--surface) p-2 shadow-sm"
		>
			{@render optionRow(allSelected, 'Select all', false, toggleAll)}

			{#each options as option (option.value)}
				{@render optionRow(
					value.includes(option.value),
					option.label,
					option.disabled ?? false,
					() => toggleOption(option.value),
					'option'
				)}
			{/each}
		</div>
	{/if}
</div>
