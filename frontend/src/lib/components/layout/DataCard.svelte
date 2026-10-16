<script lang="ts">
	import Card from './Card.svelte';
	import TitleCard from './TitleCard.svelte';

	import { 
		formatDateDDMMYYYY,
		formatTimestampDDMMYYYY,
		formatEnum,
	} from '$lib/utils/helpers';

	export type DataCardItem = {
		label: string;
		value: string | number | null | undefined;
		format?: 'date' | 'datetime' | 'enum';
	};

	type Props = {
		title: string;
		description?: string;
		data: DataCardItem[];
		href?: string;
		onclick?: (event: MouseEvent) => void;
	};

	let {
		title,
		description,
		data,
		href,
		onclick
	}: Props = $props();

	function formatValue(item: DataCardItem): string | number {
		if (item.value === null || item.value === undefined) {
			return '—';
		}

		if (typeof item.value === 'number') {
			return item.value;
		}

		switch (item.format) {
			case 'date':
				return formatDateDDMMYYYY(item.value);
			case 'datetime':
				return formatTimestampDDMMYYYY(item.value);
			case 'enum':
				return formatEnum(item.value);
			default:
				return item.value;
		}
	}
</script>

<Card 
	border={true}
	href={href}
	onclick={onclick}
>
	<TitleCard
		{title}
		{description}
	/>

	<div class="px-5 pb-5">
		{#each data as item, index}
			<div
				class="
					grid
					grid-cols-[3fr_7fr]
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
						text-xs font-extrabold
						uppercase tracking-wide
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
					{formatValue(item)}
				</div>
			</div>
		{/each}
	</div>
</Card>