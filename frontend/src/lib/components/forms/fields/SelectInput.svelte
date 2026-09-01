<script lang="ts">
	import { onMount } from 'svelte';

	import InlineError from './InlineError.svelte';

	export type SelectOption = {
		value: string;
		label: string;
		disabled?: boolean;
	};

	type Props = {
		value: string;
		label: string;
		options: SelectOption[];

		placeholder?: string;

		isDisabled?: boolean;
		isRequired?: boolean;

		error?: string | null;
	};

	let {
		value = $bindable(),
		label,
		options,

		placeholder = 'Select an option',

		isDisabled = false,
		isRequired = true,

		error
	}: Props = $props();

	let containerElement: HTMLDivElement;
	let isOpen = $state(false);

	const id = $derived(
		`${label.trim().toLowerCase().replace(/\s+/g, '-')}-input`
	);

	const selectedOption = $derived(
		options.find((option) => option.value === value)
	);

	function selectOption(option: SelectOption) {
		if (option.disabled) return;

		value = option.value;
		isOpen = false;
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
		{selectedOption?.label ?? placeholder}
	</button>

	{#if isOpen}
		<div
			role="listbox"
			class="absolute z-50"
		>
			{#each options as option (option.value)}
				<button
					type="button"
					role="option"
					disabled={option.disabled}
					aria-selected={option.value === value}
					onclick={() => selectOption(option)}
				>
					{option.label}
				</button>
			{/each}
		</div>
	{/if}

	<InlineError message={error} />
</div>