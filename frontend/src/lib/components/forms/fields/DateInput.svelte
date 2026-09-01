<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: string;
        label: string;

        name?: string;
        min?: string;
        max?: string;

        isDisabled?: boolean;
        isRequired?: boolean;

        error?: string | null;

        onchange?: (
            event: Event & {
                currentTarget: HTMLInputElement;
            },
        ) => void;
    };

    let {
        value = $bindable(),
        label,

        min,
        max,

        isDisabled = false,
        isRequired = true,

        error,

        onchange,
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
        type="date"
        {min}
        {max}
        required={isRequired}
        disabled={isDisabled}
        onchange={(event) => onchange?.(event)}
    />

    <InlineError message={error} />
</div>
