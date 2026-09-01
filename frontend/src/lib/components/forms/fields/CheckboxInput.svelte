<script lang="ts">
    import InlineError from "./InlineError.svelte";

    type Props = {
        value: boolean;
        label: string;

        isDisabled?: boolean;

        error?: string | null;
    };

    let {
        value = $bindable(),
        label,

        isDisabled = false,

        error,
    }: Props = $props();

    const name = $derived(
		label.trim().toLowerCase().replace(/\s+/g, '-')
	);
    
    const id = $derived(
		`${label.trim().toLowerCase().replace(/\s+/g, '-')}-input`
	);
</script>

<div>
    <div class="flex items-center gap-2">
        <input
            bind:checked={value}
            {id}
            {name}
            type="checkbox"
            disabled={isDisabled}
        />

        <label for={id}>
            {label}
        </label>
    </div>

    <InlineError message={error} />
</div>
