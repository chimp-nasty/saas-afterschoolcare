<script lang="ts">
	type Props = {
		title: string;
		description?: string;
	};

	let { title, description }: Props = $props();
</script>

<header class="mb-4 border-b border-(--border) px-5 py-4">
	<!-- A compact data card's title: the label role. -->
	<h2 class="label-text">
		{title}
	</h2>

	{#if description}
	<p class="mt-1 text-sm text-(--text-muted)">
		{description}
	</p>
	{/if}
</header>