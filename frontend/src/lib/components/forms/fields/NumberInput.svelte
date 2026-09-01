<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: number | null;
        label: string;

        min?: number;
        max?: number;
        step?: number;

        isDisabled?: boolean;
        isRequired?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        min,
        max,
        step,

        isDisabled = false,
        isRequired = true,

        error,
    }: Props = $props();

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

    <input
        bind:value
        {id}
        {name}
        type="number"
        {min}
        {max}
        {step}
        required={isRequired}
        disabled={isDisabled}
    />

    <InlineError message={error} />
</div>
