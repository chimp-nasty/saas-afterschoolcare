<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: string;
        label: string;

        name?: string;
        placeholder?: string;
        rows?: number;

        isDisabled?: boolean;
        isRequired?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        name,
        placeholder,
        rows = 4,

        isDisabled = false,
        isRequired = true,

        error,
    }: Props = $props();

    const id = $derived(
        name ?? `textarea-input-${crypto.randomUUID()}`,
    );
</script>

<div class="field">
    <label for={id}>
        {label}
    </label>

    <textarea
        bind:value
        {id}
        name={name ?? id}
        {placeholder}
        {rows}
        required={isRequired}
        disabled={isDisabled}
    ></textarea>

    <InlineError message={error} />
</div>
