<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: boolean;
        label: string;

        name?: string;
        isDisabled?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        name,
        isDisabled = false,

        error,
    }: Props = $props();

    const id = $derived(
        name ?? `checkbox-input-${crypto.randomUUID()}`,
    );
</script>

<div>
    <div class="flex items-center gap-2">
        <input
            bind:checked={value}
            {id}
            name={name ?? id}
            type="checkbox"
            disabled={isDisabled}
        />

        <label for={id}>
            {label}
        </label>
    </div>

    <InlineError message={error} />
</div>
