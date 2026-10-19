<!--
    A filter (MultiSelect) and a search box for a list. Stacked on mobile,
    side by side from md. No surface of its own: put it in a Card or straight
    on the page above the list.
-->
<script lang="ts">
    import { Search, X } from "lucide-svelte";

    import MultiSelect, {
        type MultiSelectOption
    } from "$lib/components/forms/fields/MultiSelect.svelte";

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
        searchPlaceholder = "Search",

        isDisabled = false,
    }: Props = $props();

    function clearSearch(): void {
        searchValue = "";
    }
</script>

<div class="flex w-full flex-col gap-4 md:flex-row md:items-end">
    <div class="w-full md:w-64 md:shrink-0">
        <MultiSelect
            bind:value={selectedValues}
            label={filterLabel}
            {options}
            placeholder={filterPlaceholder}
            {isDisabled}
        />
    </div>

    <div class="relative min-w-0 flex-1">
        <Search
            size={18}
            aria-hidden="true"
            class="pointer-events-none absolute top-1/2 left-0 -translate-y-1/2 text-(--text-muted)"
        />

        <!-- Underline input from layout.css; padded for the icons. -->
        <input
            type="search"
            bind:value={searchValue}
            placeholder={searchPlaceholder}
            disabled={isDisabled}
            aria-label={searchPlaceholder}
            class="min-h-11 pr-11 pl-7"
        />

        {#if searchValue.length > 0 && !isDisabled}
            <button
                type="button"
                class="absolute top-1/2 right-0 flex h-11 w-11 -translate-y-1/2 items-center justify-center rounded-lg text-(--text-muted) hover:text-(--text)"
                aria-label="Clear search"
                onclick={clearSearch}
            >
                <X size={18} />
            </button>
        {/if}
    </div>
</div>
