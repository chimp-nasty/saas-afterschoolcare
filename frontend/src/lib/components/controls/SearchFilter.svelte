<script lang="ts">
    import MultiSelect, {
        type MultiSelectOption
    } from "$lib/components/forms/fields/MultiSelect.svelte"

    type Props = {
        options: MultiSelectOption[];

        selectedValues?: string[];
        searchValue?: string;

        filterLabel?: string;
        filterPlaceholder?: string;
        searchPlaceholder?: string;

        isDisabled?: boolean;
    };

    let {
        options,

        selectedValues = $bindable([]),
        searchValue = $bindable(""),

        filterLabel = "Filter",
        filterPlaceholder = "Select filters",
        searchPlaceholder = "Search...",

        isDisabled = false,
    }: Props = $props();

    function clearSearch(): void {
        searchValue = "";
    }
</script>

<div
    class={[
        "flex w-full flex-col gap-3",
        "border-b border-(--border) bg-(--surface) px-5 py-4",
        "sm:flex-row sm:items-end",
    ]}
>
    <div class="w-full sm:w-64 sm:shrink-0">
        <MultiSelect
            bind:value={selectedValues}
            label={filterLabel}
            {options}
            placeholder={filterPlaceholder}
            {isDisabled}
            isRequired={false}
        />
    </div>

    <div class="relative min-w-0 flex-1">
        <span
            class={[
                "pointer-events-none absolute left-3 top-1/2",
                "-translate-y-1/2 text-(--text-muted)",
            ]}
            aria-hidden="true"
        >
            <svg
                class="size-4"
                viewBox="0 0 20 20"
                fill="none"
            >
                <circle
                    cx="8.5"
                    cy="8.5"
                    r="5.5"
                    stroke="currentColor"
                    stroke-width="1.75"
                />

                <path
                    d="M12.5 12.5L17 17"
                    stroke="currentColor"
                    stroke-width="1.75"
                    stroke-linecap="round"
                />
            </svg>
        </span>

        <input
            type="search"
            bind:value={searchValue}
            placeholder={searchPlaceholder}
            disabled={isDisabled}
            aria-label={searchPlaceholder}
            class="min-h-10 pl-10 pr-10"
        />

        {#if searchValue.length > 0 && !isDisabled}
            <button
                type="button"
                class={[
                    "absolute right-2 top-1/2 flex size-7",
                    "-translate-y-1/2 items-center justify-center",
                    "text-(--text-muted)",
                    "transition-colors",
                    "hover:bg-(--surface-muted)",
                    "hover:text-(--text)",
                    "focus-visible:outline-none",
                    "focus-visible:ring-2",
                    "focus-visible:ring-(--primary-soft)",
                ]}
                aria-label="Clear search"
                onclick={clearSearch}
            >
                <svg
                    class="size-4"
                    viewBox="0 0 20 20"
                    fill="none"
                    aria-hidden="true"
                >
                    <path
                        d="M5 5L15 15M15 5L5 15"
                        stroke="currentColor"
                        stroke-width="1.75"
                        stroke-linecap="round"
                    />
                </svg>
            </button>
        {/if}
    </div>
</div>