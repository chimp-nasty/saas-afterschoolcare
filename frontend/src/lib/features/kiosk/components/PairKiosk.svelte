<!--
    A tablet that isn't set up yet: an admin adds it in Admin › Kiosks and
    types the 8-character setup code here.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import ErrorText from '$lib/components/text/ErrorText.svelte';

	let {
		onpair
	}: {
		// Resolves to an error message, or null once paired.
		onpair: (code: string) => Promise<string | null>;
	} = $props();

	let code = $state('');
	let error = $state<string | null>(null);
	let busy = $state(false);

	async function submit(event: SubmitEvent) {
		event.preventDefault();
		busy = true;

		try {
			error = await onpair(code.trim().toUpperCase());
		} finally {
			busy = false;
		}
	}
</script>

<form class="mx-auto flex w-full max-w-md flex-col items-center gap-6 pt-12" onsubmit={submit}>
	<h1 class="text-center text-3xl font-extrabold text-(--text)">Set up this kiosk</h1>

	<p class="text-center text-lg text-(--text-muted)">
		An admin adds the kiosk in Admin › Kiosks, which shows a setup code. Type it here.
	</p>

	<label class="w-full">
		<span class="sr-only">Setup code</span>
		<input
			class="w-full text-center text-3xl font-extrabold uppercase tracking-[0.3em]"
			maxlength="8"
			autocomplete="off"
			autocapitalize="characters"
			spellcheck="false"
			bind:value={code}
			required
		/>
	</label>

	{#if error}
		<div class="w-full text-center">
			<ErrorText size="kiosk" message={error} />
		</div>
	{/if}

	<div class="w-full">
		<Button type="submit" fullWidth textSize="lg" isLoading={busy} isDisabled={busy || code.trim().length !== 8}>
			Set up kiosk
		</Button>
	</div>
</form>
