<!--
    Straight after logging in, when the family has messages they haven't
    seen: a pop-up with a ringing bell, leading to Messages. Once per login
    (loginNotice.ts); never during setup, which starts from registering.
-->
<script lang="ts">
    import { onMount } from "svelte";
    import { goto } from "$app/navigation";

    import { Bell } from "lucide-svelte";

    import Button from "$lib/components/actions/Button.svelte";
    import Modal from "$lib/components/overlays/Modal.svelte";

    import { auth } from "$lib/auth/state.svelte";

    import { takeJustLoggedIn } from "../loginNotice";

    let {
        count,
        messagesHref,
    }: {
        // Messages they haven't seen.
        count: number;
        messagesHref: string;
    } = $props();

    let modal: Modal;

    onMount(() => {
        if (takeJustLoggedIn() && count > 0) {
            modal.open();
        }
    });

    function view() {
        modal.close();
        void goto(messagesHref);
    }
</script>

<Modal
    bind:this={modal}
    title={`Hi ${$auth.firstName ?? "there"},`}
    description={count === 1 ? "You have 1 new message." : `You have ${count} new messages.`}
>
    <div class="flex justify-center py-2">
        <span class="flex size-16 items-center justify-center rounded-full bg-(--primary-soft) text-(--primary)">
            <span class="inline-flex origin-top motion-safe:animate-[bell-ring_0.6s_ease-in-out_0.3s_3]">
                <Bell size={28} />
            </span>
        </span>
    </div>

    {#snippet actions()}
        <Button variant="ghost" onclick={() => modal.close()}>Later</Button>
        <Button onclick={view}>View messages</Button>
    {/snippet}
</Modal>
