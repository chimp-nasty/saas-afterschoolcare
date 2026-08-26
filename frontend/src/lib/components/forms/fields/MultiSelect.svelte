<script lang="ts">
	import { onMount } from 'svelte';

	import InlineError from './InlineError.svelte';

	export type MultiSelectOption = {
		value: string;
		label: string;
		disabled?: boolean;
	};

	type Props = {
		value: string[];
		label: string;
		options: MultiSelectOption[];

		name?: string;
		placeholder?: string;

		isDisabled?: boolean;
		isRequired?: boolean;

		error?: string | null;
	};

	let {
		value = $bindable([]),
		label,
		options,

		name,
		placeholder = 'Select options',

		isDisabled = false,
		isRequired = true,

		error
	}: Props = $props();

	let containerElement: HTMLDivElement;
	let isOpen = $state(false);

	const id = $derived(
		name ?? `multi-select-${crypto.randomUUID()}`
	);

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
		function handleMouseDown(event: MouseEvent) {
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

		document.addEventListener('mousedown', handleMouseDown);
		document.addEventListener('keydown', handleKeyDown);

		return () => {
			document.removeEventListener('mousedown', handleMouseDown);
			document.removeEventListener('keydown', handleKeyDown);
		};
	});
</script>

<div
	class="field"
	bind:this={containerElement}
>
	<label for={id}>
		{label}
        {#if isRequired}
            <span aria-hidden="true">*</span>
        {/if}
	</label>

	<button
		{id}
		type="button"
		disabled={isDisabled}
		aria-expanded={isOpen}
		aria-haspopup="listbox"
		onclick={() => (isOpen = !isOpen)}
	>
		{triggerText}
	</button>

	{#if isOpen}
		<div
			role="listbox"
			aria-multiselectable="true"
			class="absolute z-50"
		>
			<button
				type="button"
				onclick={toggleAll}
			>
				<input
					type="checkbox"
					checked={allSelected}
					tabindex="-1"
					aria-hidden="true"
				/>

				Select all
			</button>

			{#each options as option (option.value)}
				<button
					type="button"
					role="option"
					disabled={option.disabled}
					aria-selected={value.includes(option.value)}
					onclick={() => toggleOption(option.value)}
				>
					<input
						type="checkbox"
						checked={value.includes(option.value)}
						disabled={option.disabled}
						tabindex="-1"
						aria-hidden="true"
					/>

					{option.label}
				</button>
			{/each}
		</div>
	{/if}

	<InlineError message={error} />
</div>