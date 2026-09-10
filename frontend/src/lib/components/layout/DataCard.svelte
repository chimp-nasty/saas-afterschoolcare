<script lang="ts">
	import Card from './Card.svelte';
	import TitleCard from './TitleCard.svelte';

	export type DataCardItem = {
		label: string;
		value: string | number | null | undefined;
	};

	type Props = {
		title: string;
		description?: string;
		data: DataCardItem[];
	};

	let {
		title,
		description,
		data
	}: Props = $props();
</script>

<Card border>
	<TitleCard
		{title}
		{description}
	/>

	<div class="px-5 pb-5">
		{#each data as item, index}
			<div
				class="
					grid
					grid-cols-[10rem_1fr]
					items-stretch
					{index < data.length - 1 ? 'border-b border-(--border)' : ''}
				"
			>
				<div
					class="
						flex
						items-center
						border-r border-(--border)
						py-3 pr-4
						text-sm font-semibold
						text-(--text-muted)
					"
				>
					{item.label}
				</div>

				<div
					class="
						flex
						min-w-0
						items-center
						py-3 pl-4
						text-base font-semibold
						text-(--text)
						wrap-break-word
					"
				>
					{item.value ?? '—'}
				</div>
			</div>
		{/each}
	</div>
</Card>