<!--
    The platform's feature cards, edited inline (EditableSection): up to 9,
    each an icon from a fixed set (picked from the icons themselves) with a
    title and a line. Choosing an icon suggests its wording, unless the
    card's own has been written.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';

	import type { PlatformFeatureItem } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';
	import {
		PLATFORM_FEATURE_ICON_NAMES,
		PLATFORM_FEATURE_ICONS,
		presetFeature,
		type PlatformFeatureIcon
	} from '../features';

	const MAX_FEATURES = 9;

	let {
		initial,
		onsubmit,
		oncancel
	}: {
		initial: PlatformFeatureItem[];
		onsubmit: (features: PlatformFeatureItem[]) => Promise<ApiResponse<unknown>>;
		oncancel?: () => void;
	} = $props();

	// The saved list when the editor opens; it then owns its edits.
	let features = $state<PlatformFeatureItem[]>(untrack(() => initial.map((feature) => ({ ...feature }))));
	let isLoading = $state(false);

	function chooseIcon(feature: PlatformFeatureItem, icon: PlatformFeatureIcon) {
		const previous = PLATFORM_FEATURE_ICONS[feature.icon];
		const untouched = feature.title === previous.title && feature.text === previous.text;

		feature.icon = icon;

		if (untouched) {
			feature.title = PLATFORM_FEATURE_ICONS[icon].title;
			feature.text = PLATFORM_FEATURE_ICONS[icon].text;
		}
	}

	function move(index: number, by: number) {
		const target = index + by;

		if (target < 0 || target >= features.length) return;

		[features[index], features[target]] = [features[target], features[index]];
	}

	// The next icon not in use yet.
	function add() {
		const unused = PLATFORM_FEATURE_ICON_NAMES.find((icon) => !features.some((feature) => feature.icon === icon));

		features.push(presetFeature(unused ?? 'privacy'));
	}

	async function submit() {
		isLoading = true;

		try {
			await onsubmit(features.map((feature) => ({ ...feature })));
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save features" {oncancel}>
	{#each features as feature, index (index)}
		<div class="flex flex-col gap-3 border-b border-(--border) pb-4">
			<!-- The icons as they look on the page; the chosen one is marked. -->
			<div class="flex flex-col gap-2">
				<p class="label-text" id={`feature-${index}-icon`}>Feature {index + 1}: icon</p>

				<div class="flex flex-wrap gap-2" role="radiogroup" aria-labelledby={`feature-${index}-icon`}>
					{#each PLATFORM_FEATURE_ICON_NAMES as icon (icon)}
						{@const Icon = PLATFORM_FEATURE_ICONS[icon].icon}
						{@const chosen = feature.icon === icon}

						<button
							type="button"
							role="radio"
							aria-checked={chosen}
							aria-label={PLATFORM_FEATURE_ICONS[icon].name}
							title={PLATFORM_FEATURE_ICONS[icon].name}
							class={[
								'flex size-12 items-center justify-center rounded-lg border-2 transition',
								chosen
									? 'border-(--primary) bg-(--accent-soft) text-(--primary)'
									: 'border-(--border) bg-(--surface) text-(--text-muted) hover:border-(--primary) hover:text-(--primary)'
							]}
							onclick={() => chooseIcon(feature, icon)}
						>
							<Icon size={22} aria-hidden="true" />
						</button>
					{/each}
				</div>
			</div>

			<Field label="Title">
				{#snippet children(id)}
					<input {id} type="text" maxlength="60" bind:value={feature.title} required />
				{/snippet}
			</Field>

			<Field label="Line">
				{#snippet children(id)}
					<input {id} type="text" maxlength="200" bind:value={feature.text} required />
				{/snippet}
			</Field>

			<div class="flex flex-wrap gap-3">
				<Button variant="ghost" isDisabled={index === 0} onclick={() => move(index, -1)}>Move up</Button>
				<Button variant="ghost" isDisabled={index === features.length - 1} onclick={() => move(index, 1)}>
					Move down
				</Button>
				<Button variant="ghost" onclick={() => features.splice(index, 1)}>Remove</Button>
			</div>
		</div>
	{:else}
		<EmptyState message="No features: none show on the page." />
	{/each}

	{#if features.length < MAX_FEATURES}
		<div>
			<Button variant="ghost" onclick={add}>Add a feature</Button>
		</div>
	{/if}
</Form>
