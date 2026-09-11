<script lang="ts">
    let {
        page,
        hasNext,
        isLoading = false,
        onPrevious,
        onNext,
    }: {
        page: number;
        hasNext: boolean;
        isLoading?: boolean;
        onPrevious: () => void | Promise<void>;
        onNext: () => void | Promise<void>;
    } = $props();
</script>

<div
    class="
        flex items-center justify-between
        border-t border-(--border) pt-4
    "
>
    <button
        type="button"
        disabled={page <= 1 || isLoading}
        onclick={onPrevious}
        class="
            text-sm font-semibold text-(--text)
            disabled:cursor-not-allowed
            disabled:opacity-40
        "
    >
        ← Previous
    </button>

    <span class="text-sm text-(--text-muted)">
        Page {page}
    </span>

    <button
        type="button"
        disabled={!hasNext || isLoading}
        onclick={onNext}
        class="
            text-sm font-semibold text-(--text)
            disabled:cursor-not-allowed
            disabled:opacity-40
        "
    >
        Next →
    </button>
</div>