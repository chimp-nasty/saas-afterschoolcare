<!--
    The business's questions and answers on its public pages (the landing
    page and every centre's), each opening in place.
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';

	import type { PublicFaqResponse } from '$lib/api/schema';

	let {
		faqs
	}: {
		faqs: PublicFaqResponse[];
	} = $props();
</script>

<div class="max-w-3xl">
	<Card border padded={false}>
		{#each faqs as faq, index (index)}
			<details class="group border-b border-(--border) last:border-b-0">
				<summary class="flex min-h-12 cursor-pointer items-center px-5 py-3 text-base font-semibold text-(--text)">
					{faq.question}
				</summary>

				<p class="whitespace-pre-line px-5 pb-4 text-base text-(--text)">{faq.answer}</p>
			</details>
		{/each}
	</Card>
</div>
