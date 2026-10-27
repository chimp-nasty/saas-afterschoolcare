<!--
    A public site band's heading (docs/public-site.md): a short accent bar,
    an optional eyebrow, the title (headline-text) and an optional line under
    it. The accent colour is only ever decoration here, never text: a
    business may pick one too light to read on white.
-->
<script lang="ts">
	let {
		title,
		eyebrow,
		description
	}: {
		title: string;
		eyebrow?: string | null;
		description?: string | null;
	} = $props();
</script>

<div class="flex max-w-3xl flex-col gap-3">
	<span class="h-1 w-10 rounded-full bg-(--accent)" aria-hidden="true"></span>

	{#if eyebrow}
		<p class="label-text">{eyebrow}</p>
	{/if}

	<h2 class="headline-text">{title}</h2>

	{#if description}
		<p class="text-base text-(--text-muted) md:text-lg">{description}</p>
	{/if}
</div>
