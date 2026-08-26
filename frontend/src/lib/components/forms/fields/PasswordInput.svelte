<script lang="ts">
	import InlineError from './InlineError.svelte';

	type Props = {
		value: string;
		label: string;

		name?: string;
		placeholder?: string;

		isDisabled?: boolean;
		isRequired?: boolean;

		error?: string | null;
	};

	let {
		value = $bindable(),
		label,

		name,
		placeholder,

		isDisabled = false,
		isRequired = true,

		error
	}: Props = $props();

	let isVisible = $state(false);

	const id = $derived(
		name ?? `password-input-${crypto.randomUUID()}`
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
			name={name ?? id}
			type={isVisible ? 'text' : 'password'}
			{placeholder}
			required={isRequired}
			disabled={isDisabled}
		/>

		<button
			type="button"
			aria-label={isVisible ? 'Hide password' : 'Show password'}
			onclick={() => (isVisible = !isVisible)}
		>
			{isVisible ? 'Hide' : 'Show'}
		</button>
	</div>

	<InlineError message={error} />
</div>