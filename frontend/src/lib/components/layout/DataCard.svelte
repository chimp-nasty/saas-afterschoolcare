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
		value: string | number | Date | null | undefined;
		format?: 'date' | 'enum';
	};

	type Props = {
		title: string;
		description?: string;
		data: DataCardItem[];
		href?: string;
	};

	let {
		title,
		description,
		data,
		href
	}: Props = $props();

	function formatValue(item: DataCardItem): string | number {
		if (item.value === null || item.value === undefined) {
			return '—';
		}

		if (item.value instanceof Date) {
			return formatTimestampDDMMYYYY(item.value);
		}

		if (item.format === 'enum' && typeof item.value === 'string') {
			return formatEnum(item.value);
		}

		return item.value;
	}
</script>

<Card 
	border={true}
	href={href}
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