<script lang="ts">
	import InlineError from './InlineError.svelte';

	type Props = {
		value: string;
		label: string;

		placeholder?: string;

		isDisabled?: boolean;
		isRequired?: boolean;

		error?: string | null;
	};

	let {
		value = $bindable(),
		label,

		placeholder,

		isDisabled = false,
		isRequired = true,

		error
	}: Props = $props();

	let isVisible = $state(false);

	const name = $derived(
		label.trim().toLowerCase().replace(/\s+/g, '-')
	);
	
	const id = $derived(
		`${label.trim().toLowerCase().replace(/\s+/g, '-')}-input`
	);
</script>

<div class="field">
	<label for={id}>
		{label}
	</label>

	<div class="relative">
		<input
			bind:value
			{id}
			{name}
			type={isVisible ? 'text' : 'password'}
			{placeholder}
			required={isRequired}
			disabled={isDisabled}
		/>
	</div>

	<InlineError message={error} />
</div>