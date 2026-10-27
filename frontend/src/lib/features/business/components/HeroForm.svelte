<!--
    The hero's headline and paragraph (the landing page and every centre's
    page), edited inline where they're shown (EditableSection). Sends only
    these two fields, so the colours are left as they are.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { SiteRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	type HeroRequest = Pick<SiteRequest, 'tagline' | 'hero_text'>;

	let {
		initial,
		onsubmit,
		oncancel
	}: {
		initial: HeroRequest;
		onsubmit: SubmitHandler<HeroRequest>;
		oncancel?: () => void;
	} = $props();

	// The saved values when the form opens; it then owns its edits.
	let tagline = $state(untrack(() => initial.tagline ?? ''));
	let heroText = $state(untrack(() => initial.hero_text ?? ''));

	let errors = $state<FormErrors<HeroRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({ tagline: tagline || null, hero_text: heroText || null });

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save" {oncancel}>
	<Field label="Headline (e.g. A welcoming place after school)" error={errors.tagline}>
		{#snippet children(id)}
			<input {id} type="text" maxlength="120" bind:value={tagline} />
		{/snippet}
	</Field>

	<Field label="Under the headline: a sentence or two about what you offer" error={errors.hero_text}>
		{#snippet children(id)}
			<textarea {id} rows="3" maxlength="300" bind:value={heroText}></textarea>
		{/snippet}
	</Field>
</Form>
