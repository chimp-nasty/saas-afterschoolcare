<!--
    The landing page's questions and answers (Business settings › Your
    site): add, edit, reorder and remove, then save the whole list (at most
    20; the server checks).
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Button from '$lib/components/actions/Button.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';
	import EmptyState from '$lib/components/text/EmptyState.svelte';

	import type { FaqItem } from '$lib/api/schema';
	import type { ApiResponse } from '$lib/api/wrapper';

	let {
		initial,
		onsubmit
	}: {
		initial: FaqItem[];
		onsubmit: (faqs: FaqItem[]) => Promise<ApiResponse<unknown>>;
	} = $props();

	// The saved list when the editor opens; it then owns its edits.
	let faqs = $state<FaqItem[]>(untrack(() => initial.map((faq) => ({ ...faq }))));
	let isLoading = $state(false);

	function move(index: number, by: number) {
		const target = index + by;

		if (target < 0 || target >= faqs.length) return;

		[faqs[index], faqs[target]] = [faqs[target], faqs[index]];
	}

	async function submit() {
		isLoading = true;

		try {
			await onsubmit(faqs.map((faq) => ({ ...faq })));
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save questions">
	{#each faqs as faq, index (index)}
		<div class="flex flex-col gap-3 border-b border-(--border) pb-4">
			<Field label={`Question ${index + 1}`}>
				{#snippet children(id)}
					<input {id} type="text" maxlength="200" bind:value={faq.question} required />
				{/snippet}
			</Field>

			<Field label="Answer">
				{#snippet children(id)}
					<textarea {id} rows="3" maxlength="2000" bind:value={faq.answer} required></textarea>
				{/snippet}
			</Field>

			<div class="flex flex-wrap gap-3">
				<Button variant="ghost" isDisabled={index === 0} onclick={() => move(index, -1)}>Move up</Button>
				<Button variant="ghost" isDisabled={index === faqs.length - 1} onclick={() => move(index, 1)}>Move down</Button>
				<Button variant="ghost" onclick={() => faqs.splice(index, 1)}>Remove</Button>
			</div>
		</div>
	{:else}
		<EmptyState message="No questions yet." />
	{/each}

	{#if faqs.length < 20}
		<div>
			<Button variant="ghost" onclick={() => faqs.push({ question: '', answer: '' })}>Add a question</Button>
		</div>
	{/if}
</Form>
