<script lang="ts">
	type Props = {
		title: string;
		description?: string;
	};

	let { title, description }: Props = $props();
</script>

<header class="mb-4 border-b border-(--border) px-5 py-4">
	<h2 class="text-sm font-extrabold uppercase tracking-wide text-(--text-muted)">
		{title}
	</h2>

	{#if description}
	<p class="mt-1 text-sm text-(--text)">
		{description}
	</p>
	{/if}
</header>