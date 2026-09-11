<script lang="ts">
    import { onMount } from "svelte";

    let {
        disabled = false,
        onTrigger,
    }: {
        disabled?: boolean;
        onTrigger: () => void | Promise<void>;
    } = $props();

    let trigger: HTMLDivElement;

    onMount(() => {
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (
                    !entry?.isIntersecting ||
                    disabled
                ) {
                    return;
                }

                void onTrigger();
            },
            {
                root: null,
                rootMargin: "200px 0px",
                threshold: 0
            }
        );

        observer.observe(trigger);

        return () => {
            observer.disconnect();
        };
    });
</script>

<div
    bind:this={trigger}
    class="h-1 w-full"
    aria-hidden="true"
></div>