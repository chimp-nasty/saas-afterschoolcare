<!--
    A labelled date field: Field around a native date input (which gives
    phones their own date picker). Same as writing the Field by hand, for
    when min/max or an onchange are needed.
-->
<script lang="ts">
    import Field from "../Field.svelte";

    type Props = {
        value: string;
        label: string;

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
        value = $bindable(""),
        label,

        min,
        max,

        isDisabled = false,
        isRequired = true,

        error,

        onchange,
    }: Props = $props();
</script>

<Field {label} {error}>
    {#snippet children(id)}
        <input
            bind:value
            {id}
            type="date"
            {min}
            {max}
            required={isRequired}
            disabled={isDisabled}
            onchange={(event) => onchange?.(event)}
        />
    {/snippet}
</Field>
