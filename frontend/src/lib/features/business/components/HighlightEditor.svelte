<!--
    The highlights under the hero, edited inline (EditableSection): up to 4,
    each an icon from a fixed set (picked from the icons themselves) with a
    title and a line. Choosing an icon suggests its wording, which the owner
    may change. Before any are saved it starts with four suggestions;
    nothing shows on the site until saved.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';
	import Notice from '$lib/components/text/Notice.svelte';

	import type { HighlightItem } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';
	import {
		HIGHLIGHT_ICONS,
		HIGHLIGHT_PRESETS,
		SUGGESTED_HIGHLIGHTS,
		presetHighlight,
		type HighlightIcon
	} from '../highlights';

	const MAX_HIGHLIGHTS = 4;

	let {
		initial,
		onsubmit,
		oncancel
	}: {
		initial: HighlightItem[];
		onsubmit: (highlights: HighlightItem[]) => Promise<ApiResponse<unknown>>;
		// Inline (EditableSection): back to the section without saving.
		oncancel?: () => void;
	} = $props();

	// The saved list when the editor opens (or the suggestions); it then owns
	// its edits.
	let isSuggested = $state(untrack(() => initial.length === 0));

	let highlights = $state<HighlightItem[]>(
		untrack(() =>
			isSuggested ? SUGGESTED_HIGHLIGHTS.map(presetHighlight) : initial.map((highlight) => ({ ...highlight }))
		)
	);
	let isLoading = $state(false);

	// A new icon brings its wording, unless the owner has written their own.
	function chooseIcon(highlight: HighlightItem, icon: HighlightIcon) {
		const previous = HIGHLIGHT_PRESETS[highlight.icon];
		const untouched = highlight.title === previous.title && highlight.text === previous.text;

		highlight.icon = icon;

		if (untouched) {
			highlight.title = HIGHLIGHT_PRESETS[icon].title;
			highlight.text = HIGHLIGHT_PRESETS[icon].text;
		}
	}

	function move(index: number, by: number) {
		const target = index + by;

		if (target < 0 || target >= highlights.length) return;

		[highlights[index], highlights[target]] = [highlights[target], highlights[index]];
	}

	// The next icon not in use yet.
	function add() {
		const unused = HIGHLIGHT_ICONS.find((icon) => !highlights.some((highlight) => highlight.icon === icon));

		highlights.push(presetHighlight(unused ?? 'shield'));
	}

	async function submit() {
		isLoading = true;

		try {
			const response = await onsubmit(highlights.map((highlight) => ({ ...highlight })));

			if (response.ok) isSuggested = false;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save highlights" {oncancel}>
	{#if isSuggested}
		<Notice>These are suggestions: change them as you like. They show on your site once you save.</Notice>
	{/if}

	{#each highlights as highlight, index (index)}
		<div class="flex flex-col gap-3 border-b border-(--border) pb-4">
			<!-- The icons as they look on the site; the chosen one is marked. -->
			<div class="flex flex-col gap-2">
				<p class="label-text" id={`highlight-${index}-icon`}>Highlight {index + 1}: icon</p>

				<div class="flex flex-wrap gap-2" role="radiogroup" aria-labelledby={`highlight-${index}-icon`}>
					{#each HIGHLIGHT_ICONS as icon (icon)}
						{@const Icon = HIGHLIGHT_PRESETS[icon].icon}
						{@const chosen = highlight.icon === icon}

						<button
							type="button"
							role="radio"
							aria-checked={chosen}
							aria-label={HIGHLIGHT_PRESETS[icon].title}
							title={HIGHLIGHT_PRESETS[icon].title}
							class={[
								'flex size-12 items-center justify-center rounded-lg border-2 transition',
								chosen
									? 'border-(--primary) bg-(--accent-soft) text-(--primary)'
									: 'border-(--border) bg-(--surface) text-(--text-muted) hover:border-(--primary) hover:text-(--primary)'
							]}
							onclick={() => chooseIcon(highlight, icon)}
						>
							<Icon size={22} aria-hidden="true" />
						</button>
					{/each}
				</div>
			</div>

			<Field label="Title">
				{#snippet children(id)}
					<input {id} type="text" maxlength="60" bind:value={highlight.title} required />
				{/snippet}
			</Field>

			<Field label="Line">
				{#snippet children(id)}
					<input {id} type="text" maxlength="160" bind:value={highlight.text} required />
				{/snippet}
			</Field>

			<div class="flex flex-wrap gap-3">
				<Button variant="ghost" isDisabled={index === 0} onclick={() => move(index, -1)}>Move up</Button>
				<Button variant="ghost" isDisabled={index === highlights.length - 1} onclick={() => move(index, 1)}>
					Move down
				</Button>
				<Button variant="ghost" onclick={() => highlights.splice(index, 1)}>Remove</Button>
			</div>
		</div>
	{:else}
		<EmptyState message="No highlights: none show on your site." />
	{/each}

	{#if highlights.length < MAX_HIGHLIGHTS}
		<div>
			<Button variant="ghost" onclick={add}>Add a highlight</Button>
		</div>
	{/if}
</Form>
