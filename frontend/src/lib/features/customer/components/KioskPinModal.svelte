<!--
    "Your kiosk PIN is on its way": shown when a family adds their first
    child, which is what emails the account holder their kiosk PIN
    (children_create.py). In setup and in Account › Children. Open it with
    open(); `onclose` runs however it's closed.
-->
<script lang="ts">
	import { KeyRound } from 'lucide-svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Modal from '$lib/components/overlays/Modal.svelte';

	let {
		email,
		centreName,
		onclose
	}: {
		// Where the PIN went: their login email.
		email: string | null;
		centreName: string;
		onclose?: () => void;
	} = $props();

	let modal: Modal;

	export function open() {
		modal.open();
	}
</script>

<Modal
	bind:this={modal}
	title="Your kiosk PIN is on its way"
	description={`We've emailed a kiosk PIN to ${email ?? 'your email address'}.`}
	{onclose}
>
	<div class="flex justify-center py-2">
		<span class="flex size-16 items-center justify-center rounded-full bg-(--primary-soft) text-(--primary)">
			<KeyRound size={28} />
		</span>
	</div>

	<ul class="flex list-disc flex-col gap-2 pl-5 text-base text-(--text)">
		<li>You'll use it with your mobile number at the kiosk in {centreName} to sign your children in and out.</li>
		<li>The first time you use the kiosk, you'll choose your own 4-digit PIN. The emailed one works for 30 days.</li>
		<li>Lost it? Tap <span class="font-semibold">Forgot PIN</span> at the kiosk and we'll email a new one.</li>
	</ul>

	{#snippet actions()}
		<Button onclick={() => modal.close()}>Got it</Button>
	{/snippet}
</Modal>
