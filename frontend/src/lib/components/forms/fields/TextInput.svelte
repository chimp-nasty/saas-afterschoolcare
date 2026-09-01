<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: string;
        label: string;

        placeholder?: string;

        readonly?: boolean;
        isDisabled?: boolean;
        isRequired?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        placeholder,

        readonly = false,
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
        type="text"
        {placeholder}
        required={isRequired}
        disabled={isDisabled}
        {readonly}
    />

    <InlineError message={error} />
</div>
