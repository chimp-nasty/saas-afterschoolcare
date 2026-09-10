<script lang="ts">
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

	const id = $derived(
		`${label.trim().toLowerCase().replace(/\s+/g, '-')}-input`
	);
</script>

<div class="field">
	<label for={id}>
		{label}
		{#if isRequired}
			<span aria-hidden="true">*</span>
		{/if}
	</label>

	<select
		{id}
		bind:value
		disabled={isDisabled}
		required={isRequired}
		aria-invalid={error ? 'true' : undefined}
	>
		{#if placeholder}
			<option value="">
				{placeholder}
			</option>
		{/if}

		{#each options as option (option.value)}
			<option
				value={option.value}
				disabled={option.disabled}
			>
				{option.label}
			</option>
		{/each}
	</select>

	<InlineError message={error} />
</div>