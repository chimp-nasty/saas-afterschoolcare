<!--
    One of the business's site files (Business settings › Your site): its
    logo, site icon or a policy PDF. Says whether there is one, opens it,
    and uploads a new one (replacing an image; a policy adds a version), or
    removes an image. The page does the upload; this owns the picking.
-->
<script lang="ts">
	import Button from '$lib/components/actions/Button.svelte';
	import HyperTextLink from '$lib/components/actions/HyperTextLink.svelte';
	import SectionHeading from '$lib/components/text/SectionHeading.svelte';

	let {
		title,
		description,
		accept,
		status,
		viewHref = null,
		onupload,
		onremove
	}: {
		title: string;
		description: string;
		// The file input's accept list, e.g. "image/png".
		accept: string;
		// How it stands, e.g. "Uploaded 3 Nov" or "None yet".
		status: string;
		viewHref?: string | null;
		onupload: (file: File) => Promise<boolean>;
		onremove?: () => Promise<void>;
	} = $props();

	let input = $state<HTMLInputElement | null>(null);
	let isBusy = $state(false);

	async function picked(event: Event) {
		const file = (event.currentTarget as HTMLInputElement).files?.[0];

		if (!file) return;

		isBusy = true;

		try {
			await onupload(file);
		} finally {
			isBusy = false;

			if (input) input.value = '';
		}
	}

	async function remove() {
		if (!onremove) return;

		isBusy = true;

		try {
			await onremove();
		} finally {
			isBusy = false;
		}
	}
</script>

<div class="flex flex-col gap-3">
	<SectionHeading {title} {description} />

	<p class="text-sm text-(--text-muted)">{status}</p>

	{#if viewHref}
		<HyperTextLink href={viewHref} external>View current</HyperTextLink>
	{/if}

	<input bind:this={input} type="file" {accept} class="hidden" onchange={picked} />

	<div class="flex flex-wrap gap-3">
		<Button variant="ghost" isLoading={isBusy} onclick={() => input?.click()}>
			{viewHref ? 'Upload a new one' : 'Upload'}
		</Button>

		{#if onremove && viewHref}
			<Button variant="ghost" isLoading={isBusy} onclick={remove}>Remove</Button>
		{/if}
	</div>
</div>
