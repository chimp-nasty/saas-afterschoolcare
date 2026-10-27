<!--
    Page text edited where it's shown (docs/public-site.md, section 6). For
    whoever may edit it, on desktop: a pencil at the top right that swaps
    the content for `editor`, in place; the editor calls `done` to go back
    (after saving, or Cancel). An empty section shows them a prompt to add
    it instead. Everyone else, and every phone, sees just the content, or
    nothing when it's empty.

    It holds no data and saves nothing: the page passes the editor (a form
    whose save it owns) and decides `canEdit`. Hiding the pencil isn't the
    protection; the API refuses anyone else.
-->
<script lang="ts">
	import type { Snippet } from 'svelte';

	import { Pencil, Plus } from 'lucide-svelte';

	let {
		canEdit,
		label,
		isEmpty = false,
		emptyPrompt,
		children,
		editor
	}: {
		canEdit: boolean;
		// What's edited, for "Edit {label}" (e.g. "the highlights").
		label: string;
		isEmpty?: boolean;
		// Shown to whoever can edit when there's nothing yet.
		emptyPrompt?: string;
		children: Snippet;
		editor: Snippet<[() => void]>;
	} = $props();

	let editing = $state(false);

	function done() {
		editing = false;
	}
</script>

{#if canEdit && editing}
	<div class="hidden md:block">
		{@render editor(done)}
	</div>

	<!-- A phone never edits: it shows the page as everyone sees it. -->
	<div class="md:hidden">
		{#if !isEmpty}{@render children()}{/if}
	</div>
{:else if canEdit && isEmpty}
	<button
		type="button"
		class="hidden min-h-24 w-full items-center justify-center gap-2 rounded-2xl border-2 border-dashed border-(--border) text-base font-semibold text-(--text-muted) hover:border-(--primary) hover:text-(--primary) md:flex"
		onclick={() => (editing = true)}
	>
		<Plus size={20} aria-hidden="true" />
		{emptyPrompt ?? `Add ${label}`}
	</button>
{:else if !isEmpty}
	<div class="relative">
		{@render children()}

		{#if canEdit}
			<button
				type="button"
				class="absolute -top-2 right-0 hidden size-11 items-center justify-center rounded-full border border-(--border) bg-(--surface) text-(--text) shadow-sm hover:border-(--primary) hover:text-(--primary) md:flex"
				aria-label={`Edit ${label}`}
				title={`Edit ${label}`}
				onclick={() => (editing = true)}
			>
				<Pencil size={18} aria-hidden="true" />
			</button>
		{/if}
	</div>
{/if}
