<!--
    The feature cards on the platform's landing page: each an icon, a title
    and a line. One column on a phone, two from md, three from lg. The icon
    sits on the accent colour, softened (decoration only).
-->
<script lang="ts">
	import Card from '$lib/components/layout/Card.svelte';

	import type { PlatformFeatureItem } from '$lib/api/schema';
	import { PLATFORM_FEATURE_ICONS } from '../features';

	let {
		features
	}: {
		features: PlatformFeatureItem[];
	} = $props();
</script>

<ul class="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
	{#each features as feature, index (index)}
		{@const Icon = PLATFORM_FEATURE_ICONS[feature.icon].icon}

		<li class="flex">
			<Card border>
				<div class="flex flex-col gap-4">
					<span class="flex size-12 items-center justify-center rounded-2xl bg-(--accent-soft) text-(--primary)">
						<Icon size={24} aria-hidden="true" />
					</span>

					<div class="flex flex-col gap-2">
						<p class="text-lg font-extrabold text-(--text)">{feature.title}</p>
						<p class="text-base text-(--text-muted)">{feature.text}</p>
					</div>
				</div>
			</Card>
		</li>
	{/each}
</ul>
