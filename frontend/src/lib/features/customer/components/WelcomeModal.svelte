<!--
    Straight after registering, over the first step of /setup: a welcome
    from the business and the four setup steps, each box ticking in turn
    (all at once with reduced motion). The boxes only show what's coming;
    they can't be clicked. Get started closes it, leaving the family on the
    setup step underneath. Once (welcome.ts).
-->
<script lang="ts">
    import { onMount } from "svelte";
    import { scale } from "svelte/transition";

    import { Check } from "lucide-svelte";

    import Button from "$lib/components/actions/Button.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";

    import { SETUP_STEPS, SETUP_STEP_TITLES } from "../setup";
    import { takeJustRegistered } from "../welcome";

    let { businessName }: { businessName: string } = $props();

    // When the first box ticks, then the time between boxes.
    const FIRST_TICK_MS = 600;
    const TICK_EVERY_MS = 450;

    let modal: Modal;
    let ticked = $state(0);

    onMount(() => {
        if (!takeJustRegistered()) return;

        modal.open();

        if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
            ticked = SETUP_STEPS.length;
            return;
        }

        const timers = SETUP_STEPS.map((_, index) =>
            setTimeout(() => (ticked = index + 1), FIRST_TICK_MS + index * TICK_EVERY_MS)
        );

        return () => timers.forEach(clearTimeout);
    });
</script>

<Modal
    bind:this={modal}
    title={`Welcome to ${businessName}`}
    description="Let's get your account ready to book. It takes a few minutes, each step saves as you go, and you can stop any time."
>
    <ol class="flex flex-col gap-3" aria-label="Setting up your account">
        {#each SETUP_STEPS as step, index (step)}
            <li class="flex min-h-11 items-center gap-3">
                <span
                    class={[
                        "flex size-6 shrink-0 items-center justify-center rounded-lg border-2 transition-colors duration-300",
                        index < ticked ? "border-(--primary) bg-(--primary) text-white" : "border-(--border) bg-(--surface)",
                    ]}
                    aria-hidden="true"
                >
                    {#if index < ticked}
                        <span class="inline-flex" in:scale={{ duration: 200, start: 0.4 }}>
                            <Check size={16} strokeWidth={3} />
                        </span>
                    {/if}
                </span>

                <span class="text-base text-(--text)">
                    <span class="text-sm text-(--text-muted)">{index + 1}.</span>
                    <span class="font-semibold">{SETUP_STEP_TITLES[step]}</span>
                    {#if step === "pickups"}
                        <span class="text-sm text-(--text-muted)">(optional)</span>
                    {/if}
                </span>
            </li>
        {/each}
    </ol>

    {#snippet actions()}
        <Button onclick={() => modal.close()}>Get started</Button>
    {/snippet}
</Modal>
