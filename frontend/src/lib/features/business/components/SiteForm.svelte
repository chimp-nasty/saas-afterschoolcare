<!--
    The landing page's headline and the business's colours (Business
    settings › Your site). Colours are the app's own until the owner
    chooses theirs; every page of the business uses them.
-->
<script lang="ts">
	import { untrack } from 'svelte';

	import CheckboxRow from '$lib/components/forms/CheckboxRow.svelte';
	import Form from '$lib/components/forms/Form.svelte';
	import Field from '$lib/components/forms/Field.svelte';

	import type { SiteRequest } from '$lib/api/schema';
	import type { FormErrors, SubmitHandler } from '$lib/types/forms';

	let {
		initial,
		onsubmit
	}: {
		initial: SiteRequest;
		onsubmit: SubmitHandler<SiteRequest>;
	} = $props();

	// The app's own colours (routes/layout.css), shown in the pickers until
	// the owner chooses theirs.
	const DEFAULT_PRIMARY = '#5e2bff';
	const DEFAULT_SECONDARY = '#e8ffc2';

	// The saved values when the form opens; it then owns its edits.
	let tagline = $state(untrack(() => initial.tagline ?? ''));
	let ownColours = $state(untrack(() => Boolean(initial.primary_color || initial.secondary_color)));
	let primary = $state(untrack(() => initial.primary_color ?? DEFAULT_PRIMARY));
	let secondary = $state(untrack(() => initial.secondary_color ?? DEFAULT_SECONDARY));

	let errors = $state<FormErrors<SiteRequest>>({});
	let isLoading = $state(false);

	async function submit() {
		errors = {};
		isLoading = true;

		try {
			const response = await onsubmit({
				tagline: tagline || null,
				primary_color: ownColours ? primary : null,
				secondary_color: ownColours ? secondary : null
			});

			errors = response.fieldErrors;
		} finally {
			isLoading = false;
		}
	}
</script>

<Form {isLoading} handleSubmit={submit} submitLabel="Save">
	<Field label="Headline (e.g. After school care, made easy)" error={errors.tagline}>
		{#snippet children(id)}
			<input {id} type="text" maxlength="120" bind:value={tagline} />
		{/snippet}
	</Field>

	<CheckboxRow bind:checked={ownColours} title="Use our own colours" help="Otherwise your pages use the app's colours." />

	{#if ownColours}
		<div class="grid grid-cols-2 gap-4">
			<Field label="Main colour" error={errors.primary_color}>
				{#snippet children(id)}
					<input {id} type="color" class="h-12 w-full" bind:value={primary} />
				{/snippet}
			</Field>

			<Field label="Second colour" error={errors.secondary_color}>
				{#snippet children(id)}
					<input {id} type="color" class="h-12 w-full" bind:value={secondary} />
				{/snippet}
			</Field>
		</div>
	{/if}
</Form>
