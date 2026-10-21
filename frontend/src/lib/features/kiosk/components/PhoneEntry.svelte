<!--
    An Australian mobile number typed on the number pad (10 digits).
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import NumberPad from './NumberPad.svelte';
	import { formatTypedPhone } from '../kiosk';

	let {
		title,
		phone = $bindable(''),
		submitLabel = 'Next',
		error = null,
		busy = false,
		onsubmit,
		footer
	}: {
		title: string;
		phone?: string;
		submitLabel?: string;
		error?: string | null;
		busy?: boolean;
		onsubmit: (phone: string) => void | Promise<void>;
		footer?: Snippet;
	} = $props();
</script>

<div class="flex flex-col items-center gap-6">
	<h1 class="text-center text-3xl font-extrabold text-(--text)">{title}</h1>

	<p class="min-h-12 text-4xl font-extrabold tracking-wider text-(--text)" aria-live="polite">
		{formatTypedPhone(phone) || ' '}
	</p>

	{#if error}
		<p class="max-w-md text-center text-lg font-semibold text-(--danger-text)" role="alert">{error}</p>
	{/if}

	<NumberPad
		disabled={busy}
		ondigit={(digit) => {
			if (phone.length < 10) phone += digit;
		}}
		onbackspace={() => (phone = phone.slice(0, -1))}
	/>

	<div class="w-full max-w-sm">
		<Button fullWidth textSize="lg" isLoading={busy} isDisabled={phone.length !== 10 || busy} onclick={() => onsubmit(phone)}>
			{submitLabel}
		</Button>
	</div>

	{@render footer?.()}
</div>
