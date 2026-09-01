<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: string;
        label: string;

        placeholder?: string;
        rows?: number;

        isDisabled?: boolean;
        isRequired?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        placeholder,
        rows = 4,

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

    <textarea
        bind:value
        {id}
        {name}
        {placeholder}
        {rows}
        required={isRequired}
        disabled={isDisabled}
    ></textarea>

    <InlineError message={error} />
</div>
