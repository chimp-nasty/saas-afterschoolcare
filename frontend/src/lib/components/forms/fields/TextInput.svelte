<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: string;
        label: string;

        name?: string;
        placeholder?: string;

        readonly?: boolean;
        isDisabled?: boolean;
        isRequired?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        name,
        placeholder,

        readonly = false,
        isDisabled = false,
        isRequired = true,

        error,
    }: Props = $props();

    const id = $derived(
        name ?? `text-input-${crypto.randomUUID()}`,
    );
</script>

<div class="field">
    <label for={id}>
        {label}
    </label>

    <input
        bind:value
        {id}
        name={name ?? id}
        type="text"
        {placeholder}
        required={isRequired}
        disabled={isDisabled}
        {readonly}
    />

    <InlineError message={error} />
</div>
